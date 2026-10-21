"""
MỤC ĐÍCH: Kiểm chứng bỏ phiếu một lần, đồng thời, nonce trùng và rollback trên PostgreSQL.
PHỤ THUỘC: DB riêng đã nạp init.sql, STAGE5_TEST_DB_NAME, KMS tạm và hai role app/tally.
LUỒNG: Tạo cử tri giả, ký hai payload, gọi route /vote, đọc tổng phiếu bằng tally_user.
TỰ KIỂM TRA: Đặt STAGE5_TEST_DB_NAME rồi chạy python -m unittest tests.test_voting -v.
"""

import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.schemas import VoteRequest
from app.core.config import Settings
from app.crypto.crypto_service import decrypt_vote
from app.crypto.kms import KMS
from app.crypto.signature_service import build_ballot, build_cast, canonical_bytes
from app.database.models import Vote, Voter, VoterStatus
from app.main import app
from app.voting.vote import vote


class VotingPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        database_name = os.environ.get("STAGE5_TEST_DB_NAME", "")
        if re.fullmatch(r"evoting_stage5_test_[a-z0-9_]+", database_name) is None:
            self.skipTest("Chỉ chạy khi STAGE5_TEST_DB_NAME chỉ tới DB thử nghiệm riêng")

        config = Settings()
        self.app_engine = create_async_engine(make_url(config.APP_DATABASE_URL).set(database=database_name))
        self.tally_engine = create_async_engine(make_url(config.TALLY_DATABASE_URL).set(database=database_name))
        self.app_sessions = async_sessionmaker(self.app_engine, expire_on_commit=False)
        self.tally_sessions = async_sessionmaker(self.tally_engine, expire_on_commit=False)
        self.key_dir = tempfile.TemporaryDirectory()
        self.kms = KMS(self.key_dir.name)
        self.kms.ensure_keys()
        now = datetime.now(timezone.utc)
        self.settings = SimpleNamespace(
            ELECTION_ID="stage5-test", ELECTION_START=now - timedelta(days=1),
            ELECTION_END=now + timedelta(days=1), VOTE_REQUEST_MAX_AGE_SECONDS=300,
        )

    async def asyncTearDown(self):
        if hasattr(self, "app_engine"):
            await self.app_engine.dispose()
            await self.tally_engine.dispose()
            self.key_dir.cleanup()

    async def make_voter(self):
        voter_id = "T" + secrets.token_hex(9)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("ascii")
        async with self.app_sessions.begin() as session:
            session.add(Voter(
                voter_id=voter_id, full_name="Cử tri bỏ phiếu giả", activated=True,
                password_hash=b"test-hash", salt=b"0" * 16, public_key=public_key,
            ))
            await session.flush()
            session.add(VoterStatus(voter_id=voter_id))
        return voter_id, key

    def signed_request(self, voter_id, key, *, nonce=None, candidate_id=2, ts=None):
        nonce = nonce or secrets.token_hex(16)
        ts = int(datetime.now(timezone.utc).timestamp()) if ts is None else ts
        ballot = build_ballot(candidate_id, nonce, ts)
        cast = build_cast(self.settings.ELECTION_ID, voter_id, nonce, ts)

        def sign(payload):
            raw = key.sign(
                canonical_bytes(payload),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                hashes.SHA256(),
            )
            return base64.b64encode(raw).decode("ascii")

        return VoteRequest(ballot=ballot, sig_ballot=sign(ballot), sig_cast=sign(cast))

    async def submit(self, voter_id, request):
        with patch("app.voting.vote.get_settings", return_value=self.settings):
            async with self.app_sessions() as session:
                return await vote(request, voter_id, session, self.kms)

    async def vote_count(self):
        async with self.tally_sessions() as session:
            return await session.scalar(select(func.count()).select_from(Vote))

    async def test_valid_vote_commits_receipt_and_encrypted_ballot(self):
        voter_id, key = await self.make_voter()
        request = self.signed_request(voter_id, key)
        before = await self.vote_count()
        async with self.tally_sessions() as session:
            previous_ids = set((await session.execute(select(Vote.vote_id))).scalars())
        response = await self.submit(voter_id, request)
        self.assertTrue(response.success)
        self.assertEqual(response.receipt, hashlib.sha256(base64.b64decode(request.sig_cast)).hexdigest())
        self.assertEqual(await self.vote_count(), before + 1)

        async with self.app_sessions() as session:
            status = await session.get(VoterStatus, voter_id)
            self.assertTrue(status.has_voted)
            self.assertEqual(status.receipt_hash.hex(), response.receipt)
            self.assertEqual(status.sig_cast, base64.b64decode(request.sig_cast))
            self.assertEqual(status.voted_at.minute, 0)

        async with self.tally_sessions() as session:
            rows = [row for row in (await session.execute(select(Vote))).scalars()
                    if row.vote_id not in previous_ids]
            envelopes = [json.loads(decrypt_vote({
                "ciphertext": row.ciphertext, "wrapped_dek": row.wrapped_dek,
                "iv": row.iv, "tag": row.tag,
            }, self.kms)) for row in rows]
        self.assertTrue(any(item["ballot"] == request.ballot.model_dump() and
                            item["sig_ballot"] == request.sig_ballot for item in envelopes))

        with self.assertRaises(HTTPException) as error:
            await self.submit(voter_id, request)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(await self.vote_count(), before + 1)

    async def test_concurrent_requests_only_one_commits(self):
        voter_id, key = await self.make_voter()
        before = await self.vote_count()
        requests = [self.signed_request(voter_id, key) for _ in range(2)]

        async def attempt(request):
            try:
                return await self.submit(voter_id, request)
            except HTTPException as error:
                return error.status_code

        outcomes = await asyncio.wait_for(asyncio.gather(*(attempt(r) for r in requests)), timeout=15)
        self.assertEqual(sum(getattr(item, "success", False) for item in outcomes), 1)
        self.assertIn(409, outcomes)
        self.assertEqual(await self.vote_count(), before + 1)

    async def test_duplicate_nonce_rolls_back_second_voter(self):
        first_id, first_key = await self.make_voter()
        second_id, second_key = await self.make_voter()
        nonce = secrets.token_hex(16)
        await self.submit(first_id, self.signed_request(first_id, first_key, nonce=nonce))
        before = await self.vote_count()
        with self.assertRaises(HTTPException) as error:
            await self.submit(second_id, self.signed_request(second_id, second_key, nonce=nonce))
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(await self.vote_count(), before)
        async with self.app_sessions() as session:
            self.assertFalse((await session.get(VoterStatus, second_id)).has_voted)

    async def test_invalid_request_and_failure_after_vote_insert_roll_back(self):
        voter_id, key = await self.make_voter()
        before = await self.vote_count()
        invalid = self.signed_request(voter_id, key, candidate_id=999999)
        with self.assertRaises(HTTPException) as error:
            await self.submit(voter_id, invalid)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(await self.vote_count(), before)

        request = self.signed_request(voter_id, key)
        with patch("app.voting.voting_service.hashlib.sha256", side_effect=RuntimeError("test failure")):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                await self.submit(voter_id, request)
        self.assertEqual(await self.vote_count(), before)
        async with self.app_sessions() as session:
            self.assertFalse((await session.get(VoterStatus, voter_id)).has_voted)
        # Nếu nonce cũng rollback, lần gửi lại cùng request phải thành công.
        self.assertTrue((await self.submit(voter_id, request)).success)

    async def test_expired_future_and_wrong_signatures_do_not_write(self):
        voter_id, key = await self.make_voter()
        before = await self.vote_count()
        now = int(datetime.now(timezone.utc).timestamp())
        for ts in (now - 301, now + 301):
            with self.assertRaises(HTTPException) as error:
                await self.submit(voter_id, self.signed_request(voter_id, key, ts=ts))
            self.assertEqual(error.exception.status_code, 400)

        valid = self.signed_request(voter_id, key)
        bad_signature = base64.b64encode(b"0" * 256).decode("ascii")
        for changes in ({"sig_ballot": bad_signature}, {"sig_cast": bad_signature}):
            with self.assertRaises(HTTPException) as error:
                await self.submit(voter_id, valid.model_copy(update=changes))
            self.assertEqual(error.exception.status_code, 400)

        self.assertEqual(await self.vote_count(), before)
        self.assertTrue((await self.submit(voter_id, valid)).success)

    async def test_outside_election_window_does_not_write(self):
        voter_id, key = await self.make_voter()
        before = await self.vote_count()
        self.settings.ELECTION_END = datetime.now(timezone.utc) - timedelta(seconds=1)
        with self.assertRaises(HTTPException) as error:
            await self.submit(voter_id, self.signed_request(voter_id, key))
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(await self.vote_count(), before)

    async def test_route_requires_voter_jwt(self):
        route = next(route for route in app.routes if route.path == "/vote")
        self.assertIn("POST", route.methods)
        self.assertIn("require_voter", [dep.call.__name__ for dep in route.dependant.dependencies])


if __name__ == "__main__":
    unittest.main()
