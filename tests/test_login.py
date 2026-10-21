"""
MỤC ĐÍCH: Kiểm tra đăng nhập chỉ đọc voters và trả JWT đúng cử tri.
PHỤ THUỘC: unittest, session giả, hash/JWT thật; không ghi PostgreSQL.
LUỒNG: SV001 đăng nhập đúng/sai; tài khoản chưa kích hoạt hoặc không tồn tại bị từ chối.
TỰ KIỂM TRA: python -m unittest tests.test_login -v
"""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException


TEST_ENV = {
    "JWT_SECRET": "test-only-secret-not-used-outside-tests",
    "APP_DATABASE_URL": "postgresql+asyncpg://app_user:test@127.0.0.1:5433/evoting",
    "ADMIN_DATABASE_URL": "postgresql+asyncpg://admin_app:test@127.0.0.1:5433/evoting",
    "TALLY_DATABASE_URL": "postgresql+asyncpg://tally_user:test@127.0.0.1:5433/evoting",
    "ADMIN_USERNAME": "test-admin",
    "ADMIN_PASSWORD": "test-password",
    "ELECTION_ID": "test-election",
    "ELECTION_START": "2026-01-01T00:00:00Z",
    "ELECTION_END": "2026-12-31T23:59:59Z",
}

with patch.dict(os.environ, TEST_ENV):
    from app.api.schemas import LoginRequest
    from app.auth.auth import hash_password, verify_jwt
    from app.auth.login import login
    from app.main import app


class ReadOnlySession:
    def __init__(self, voter):
        self.voter = voter
        self.queries = 0

    async def execute(self, statement):
        self.queries += 1
        if statement.column_descriptions[0]["entity"].__tablename__ != "voters":
            raise AssertionError("Login chỉ được đọc voters")
        if "SV001" not in statement.compile().params.values():
            raise AssertionError("Login phải lọc theo voter_id được yêu cầu")
        return SimpleNamespace(scalar_one_or_none=lambda: self.voter)

    def add(self, *_):
        raise AssertionError("Login không được ghi DB")

    async def commit(self):
        raise AssertionError("Login không được commit")


class LoginTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash, cls.salt = hash_password("password-for-test")

    def setUp(self):
        self.voter = SimpleNamespace(
            voter_id="SV001", activated=True,
            password_hash=self.password_hash, salt=self.salt,
        )
        self.session = ReadOnlySession(self.voter)

    async def test_correct_password_returns_voter_token_and_election_id(self):
        with patch("app.auth.login.get_settings", return_value=SimpleNamespace(ELECTION_ID=TEST_ENV["ELECTION_ID"])):
            response = await login(LoginRequest(voter_id="SV001", password="password-for-test"), self.session)
        self.assertEqual(response.token_type, "bearer")
        self.assertEqual(response.election_id, TEST_ENV["ELECTION_ID"])
        self.assertEqual(verify_jwt(response.access_token)["sub"], "SV001")
        self.assertEqual(verify_jwt(response.access_token)["role"], "voter")
        self.assertEqual(self.session.queries, 1)

    async def test_wrong_password_inactive_and_unknown_use_same_error(self):
        for voter, password in (
            (self.voter, "wrong-password"),
            (SimpleNamespace(voter_id="SV001", activated=False, password_hash=None, salt=None), "password-for-test"),
            (None, "password-for-test"),
        ):
            self.session.voter = voter
            with self.assertRaises(HTTPException) as error:
                await login(LoginRequest(voter_id="SV001", password=password), self.session)
            self.assertEqual(error.exception.status_code, 401)
            self.assertEqual(error.exception.detail, "Thông tin đăng nhập không hợp lệ")

    async def test_main_registers_login_route(self):
        self.assertTrue(any(route.path == "/login" and "POST" in route.methods for route in app.routes))


if __name__ == "__main__":
    unittest.main()
