"""Kiểm tra cấp lại mã cho cử tri chưa kích hoạt mà không lộ mã trước commit.

Phụ thuộc: unittest, AppSession giả và bộ băm mã hiện có; không ghi PostgreSQL.
Luồng: chọn dòng chưa kích hoạt có khóa, đổi hash, in mã sau commit; lỗi thì không in.
Tự kiểm tra: python -m unittest tests.test_reissue_activation_codes -v
"""

import importlib
import os
import unittest
from contextlib import asynccontextmanager, redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.dialects import postgresql

from app.auth.auth import hash_activation_code, verify_activation_code


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


class ReissueActivationCodesTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, TEST_ENV):
            cls.reissue = importlib.import_module("app.database.reissue_activation_codes")

    async def test_reissues_only_unactivated_voters_after_commit(self):
        pending = SimpleNamespace(voter_id="SV002", activated=False,
                                  activation_hash=hash_activation_code("old-code"))
        active = SimpleNamespace(voter_id="SV001", activated=True, activation_hash=None)
        committed = False
        test = self

        class FakeSession:
            async def execute(self, statement):
                sql = str(statement.compile(dialect=postgresql.dialect()))
                test.assertIn("voters.activated IS false", sql)
                test.assertIn("FOR UPDATE", sql)
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [pending]))

        class FakeFactory:
            @staticmethod
            @asynccontextmanager
            async def begin():
                nonlocal committed
                yield FakeSession()
                committed = True

        output = []

        def capture_print(*parts):
            self.assertTrue(committed, "Mã chỉ được in sau commit")
            output.append(" ".join(map(str, parts)))

        with patch.object(self.reissue, "AppSession", FakeFactory), patch.object(
            self.reissue.secrets, "token_urlsafe", return_value="new-code"
        ), patch("builtins.print", side_effect=capture_print):
            await self.reissue.main()

        self.assertEqual(output, ["SV002: new-code", "Đã cấp lại mã cho 1 cử tri chưa kích hoạt."])
        self.assertTrue(verify_activation_code("new-code", pending.activation_hash))
        self.assertFalse(verify_activation_code("old-code", pending.activation_hash))
        self.assertTrue(active.activated)
        self.assertIsNone(active.activation_hash)

    async def test_commit_error_prints_no_code(self):
        pending = SimpleNamespace(voter_id="SV002", activated=False,
                                  activation_hash=hash_activation_code("old-code"))

        class FakeSession:
            async def execute(self, statement):
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [pending]))

        class FakeFactory:
            @staticmethod
            @asynccontextmanager
            async def begin():
                yield FakeSession()
                raise RuntimeError("commit failed")

        output = StringIO()
        with patch.object(self.reissue, "AppSession", FakeFactory), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                await self.reissue.main()

        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
