"""
MỤC ĐÍCH: Kiểm chứng seed, khóa dòng kích hoạt và đăng nhập trên PostgreSQL thật.
PHỤ THUỘC: DB riêng đã nạp db/init.sql; STAGE4_TEST_DB_NAME bắt đầu bằng evoting_stage4_test_.
LUỒNG: Seed hai lần trong transaction ngoài luôn rollback; kích hoạt đồng thời cử tri giả
đã commit trong DB thử nghiệm, kiểm tra chỉ một yêu cầu thành công rồi đăng nhập.
TỰ KIỂM TRA: Đặt STAGE4_TEST_DB_NAME và chạy python -m unittest tests.test_stage4_postgres -v.
"""

import asyncio
import os
import re
import secrets
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.schemas import ActivationRequest, LoginRequest
from app.api.candidates import list_candidates
from app.auth.activate import activate
from app.auth.auth import hash_activation_code, verify_jwt
from app.auth.login import login
from app.core.config import Settings, get_settings
from app.database import seed_voters
from app.database.models import Voter, VoterStatus


class Stage4PostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        database_name = os.environ.get("STAGE4_TEST_DB_NAME", "")
        if re.fullmatch(r"evoting_stage4_test_[a-z0-9_]+", database_name) is None:
            self.skipTest("Chỉ chạy khi STAGE4_TEST_DB_NAME chỉ tới DB thử nghiệm riêng")
        # Đọc URL thật từ .env thay vì cache có thể đã bị test session giả nạp trước.
        url = make_url(Settings().APP_DATABASE_URL).set(database=database_name)
        self.engine = create_async_engine(url, echo=False)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        if hasattr(self, "engine"):
            await self.engine.dispose()

    async def test_candidates_are_read_with_app_user(self):
        async with self.sessions() as session:
            candidates = await list_candidates(session)
        self.assertEqual([item.candidate_id for item in candidates], [1, 2, 3])
        self.assertEqual(len({item.name for item in candidates}), 3)

    async def test_seed_twice_preserves_existing_voters(self):
        async with self.engine.connect() as connection:
            outer = await connection.begin()
            sessions = async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            try:
                with patch.object(seed_voters, "AppSession", sessions), redirect_stdout(StringIO()) as output:
                    await seed_voters.main()
                    first = output.getvalue()
                    self.assertIn("Đã thêm 10 cử tri mới.", first)
                    output.seek(0)
                    output.truncate(0)
                    await seed_voters.main()
                    self.assertEqual(output.getvalue().strip(), "Đã thêm 0 cử tri mới.")

                async with sessions() as session:
                    result = await session.execute(select(Voter).where(Voter.voter_id == "SV001"))
                    voter = result.scalar_one()
                code = next(line.split(": ", 1)[1] for line in first.splitlines() if line.startswith("SV001: "))
                self.assertEqual(voter.activation_hash, hash_activation_code(code))
                self.assertFalse(voter.activated)
            finally:
                await outer.rollback()

    async def test_concurrent_activation_and_login(self):
        voter_id = "T" + secrets.token_hex(9)
        code = secrets.token_urlsafe(32)
        password = "test-password-123"
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("ascii")
        async with self.sessions.begin() as session:
            session.add(Voter(
                voter_id=voter_id, full_name="Cử tri thử nghiệm",
                activation_hash=hash_activation_code(code), activated=False,
            ))

        request = ActivationRequest(
            voter_id=voter_id, activation_code=code, password=password, public_key=public_key
        )

        async def attempt():
            async with self.sessions() as session:
                try:
                    return await activate(request, session)
                except HTTPException as error:
                    return error.status_code

        outcomes = await asyncio.wait_for(asyncio.gather(attempt(), attempt()), timeout=15)
        self.assertCountEqual(outcomes, [{"success": True}, 400])

        async with self.sessions() as session:
            result = await session.execute(select(Voter).where(Voter.voter_id == voter_id))
            voter = result.scalar_one()
            self.assertTrue(voter.activated)
            self.assertIsNone(voter.activation_hash)
            self.assertEqual(voter.public_key, public_key)
            count = await session.scalar(
                select(func.count()).select_from(VoterStatus).where(VoterStatus.voter_id == voter_id)
            )
            self.assertEqual(count, 1)
            response = await login(LoginRequest(voter_id=voter_id, password=password), session)
            self.assertEqual(verify_jwt(response.access_token)["sub"], voter_id)
            self.assertEqual(response.election_id, get_settings().ELECTION_ID)
            with self.assertRaises(HTTPException) as error:
                await login(LoginRequest(voter_id=voter_id, password="wrong-password"), session)
            self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
