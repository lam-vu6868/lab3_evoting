"""
MỤC ĐÍCH: Kiểm chặng 6: đăng nhập admin, chặn quyền/thời gian, đếm và từ chối phiếu lỗi.
PHỤ THUỘC: KMS tạm, phiếu mã hóa giả; STAGE6_TEST_DB_NAME cho kiểm tra quyền PostgreSQL.
LUỒNG: Dựng phiếu giả, gọi service/route, rồi đọc DB riêng bằng tally_user.
TỰ KIỂM TRA: STAGE6_TEST_DB_NAME=evoting_stage6_test_20261021 python -m unittest tests.test_tally -v.
"""

import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.schemas import AdminLoginRequest
from app.auth.auth import create_jwt, require_admin, verify_jwt
from app.auth.admin import admin_login
from app.core.config import Settings
from app.crypto.crypto_service import encrypt_vote
from app.crypto.kms import KMS
from app.main import app
from app.voting.results import results
from app.voting.tally import TallyError, tally_votes


class TallyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.key_dir = tempfile.TemporaryDirectory()
        self.kms = KMS(self.key_dir.name)
        self.kms.ensure_keys()
        self.settings = SimpleNamespace(ELECTION_END=datetime.now(timezone.utc) - timedelta(seconds=1))
        self.candidates = [SimpleNamespace(candidate_id=1, name="A"), SimpleNamespace(candidate_id=2, name="B")]

    async def asyncTearDown(self):
        self.key_dir.cleanup()

    def vote(self, candidate_id):
        envelope = json.dumps({"ballot": {"candidate_id": candidate_id}, "sig_ballot": "dGVzdA=="}).encode()
        return SimpleNamespace(**encrypt_vote(envelope, self.kms))

    def session(self, votes):
        session = MagicMock()
        session.execute = AsyncMock(side_effect=[
            MagicMock(scalars=lambda: MagicMock(all=lambda: self.candidates)),
            MagicMock(scalars=lambda: MagicMock(all=lambda: votes)),
        ])
        return session

    async def test_valid_votes_and_empty_ballot_box(self):
        result = await tally_votes(self.session([self.vote(2), self.vote(2)]), self.settings, self.kms)
        self.assertEqual(result.total_votes, 2)
        self.assertEqual([(row.candidate_id, row.votes) for row in result.results], [(1, 0), (2, 2)])
        self.assertEqual((await tally_votes(self.session([]), self.settings, self.kms)).total_votes, 0)

    async def test_early_request_never_queries_database(self):
        self.settings.ELECTION_END = datetime.now(timezone.utc) + timedelta(days=1)
        session = self.session([])
        with self.assertRaises(TallyError) as error:
            await tally_votes(session, self.settings, self.kms)
        self.assertEqual(error.exception.status_code, 403)
        session.execute.assert_not_awaited()
        with patch("app.voting.results.get_settings", return_value=self.settings):
            with self.assertRaises(HTTPException) as route_error:
                await results("admin", session, self.kms)
        self.assertEqual(route_error.exception.status_code, 403)

    async def test_bad_tag_json_and_candidate_stop_tally(self):
        valid = self.vote(1)
        corrupt = self.vote(2)
        corrupt.tag = b"0" * 16
        bad_json = SimpleNamespace(**encrypt_vote(b"not-json", self.kms))
        bad_candidate = self.vote(999)
        for invalid in (corrupt, bad_json, bad_candidate):
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaises(TallyError) as error:
                    await tally_votes(self.session([valid, invalid]), self.settings, self.kms)
                self.assertEqual(error.exception.status_code, 500)

    async def test_admin_login_and_route_role(self):
        config = Settings()
        response = await admin_login(AdminLoginRequest(
            username=config.ADMIN_USERNAME, password=config.ADMIN_PASSWORD,
        ))
        self.assertEqual(set(response.model_dump()), {"access_token", "token_type"})
        self.assertEqual(verify_jwt(response.access_token)["role"], "admin")
        with self.assertRaises(HTTPException) as error:
            await admin_login(AdminLoginRequest(username=config.ADMIN_USERNAME, password="wrong"))
        self.assertEqual(error.exception.status_code, 401)
        with self.assertRaises(HTTPException) as role_error:
            require_admin(HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_jwt("SV001", "voter")))
        self.assertEqual(role_error.exception.status_code, 403)
        route = next(route for route in app.routes if route.path == "/results")
        self.assertIn("require_admin", [dep.call.__name__ for dep in route.dependant.dependencies])
        self.assertNotIn("require_voter", [dep.call.__name__ for dep in route.dependant.dependencies])
        self.assertIn("POST", next(route for route in app.routes if route.path == "/admin/login").methods)


class TallyPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def test_tally_role_can_read_empty_tables(self):
        database_name = os.environ.get("STAGE6_TEST_DB_NAME", "")
        if re.fullmatch(r"evoting_stage6_test_[a-z0-9_]+", database_name) is None:
            self.skipTest("Chỉ chạy với database thử nghiệm riêng chặng 6")
        config = Settings()
        engine = create_async_engine(make_url(config.TALLY_DATABASE_URL).set(database=database_name))
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            with tempfile.TemporaryDirectory() as key_dir:
                kms = KMS(key_dir)
                kms.ensure_keys()
                settings = SimpleNamespace(ELECTION_END=datetime.now(timezone.utc) - timedelta(seconds=1))
                async with sessions() as session:
                    result = await tally_votes(session, settings, kms)
            self.assertEqual(result.total_votes, 0)
            self.assertEqual(len(result.results), 3)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    unittest.main()
