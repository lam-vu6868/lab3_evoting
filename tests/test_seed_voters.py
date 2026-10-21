"""
FILE: tests/test_seed_voters.py
MỤC ĐÍCH: Kiểm tra seed chỉ cấp mã cho cử tri mới và không lộ mã khi transaction lỗi.
PHỤ THUỘC: unittest; AppSession giả; không kết nối hoặc ghi PostgreSQL.
LUỒNG: Chạy seed hai lần trên dữ liệu giả, rồi gây lỗi INSERT để kiểm tra rollback.
TỰ KIỂM TRA: python -m unittest tests.test_seed_voters -v
"""

import importlib
import os
import unittest
from contextlib import asynccontextmanager, redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.dialects import postgresql

from app.auth.auth import hash_activation_code


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


class SeedVotersTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, TEST_ENV):
            cls.seed = importlib.import_module("app.database.seed_voters")

    async def test_only_new_voters_receive_codes_after_commit(self):
        rows = {}
        committed = False

        class FakeSession:
            async def execute(self, statement):
                compiled = statement.compile(dialect=postgresql.dialect())
                self_test.assertIn("ON CONFLICT (voter_id) DO NOTHING", str(compiled))
                self_test.assertNotIn("RETURNING", str(compiled))
                values = compiled.params
                voter_id = values["voter_id"]
                if voter_id in rows:
                    return SimpleNamespace(rowcount=0)
                rows[voter_id] = values
                return SimpleNamespace(rowcount=1)

        class FakeFactory:
            @staticmethod
            @asynccontextmanager
            async def begin():
                nonlocal committed
                committed = False
                try:
                    yield FakeSession()
                except Exception:
                    rows.clear()
                    raise
                else:
                    committed = True

        self_test = self
        output = []

        def capture_print(*values):
            self.assertTrue(committed, "Mã chỉ được in sau commit")
            output.append(" ".join(map(str, values)))

        codes = [f"fake-code-{number:02}" for number in range(1, 41)]
        with patch.object(self.seed, "AppSession", FakeFactory), patch.object(
            self.seed.secrets, "token_urlsafe", side_effect=codes
        ), patch("builtins.print", side_effect=capture_print):
            await self.seed.main()
            first_output = "\n".join(output)
            self.assertTrue(committed)
            self.assertEqual(len(rows), 20)
            for number in range(1, 21):
                voter_id = f"SV{number:03}" if number <= 10 else f"SV{number:04}"
                code = codes[number - 1]
                self.assertIn(f"{voter_id}: {code}", first_output)
                self.assertEqual(rows[voter_id]["activation_hash"], hash_activation_code(code))
                self.assertFalse(rows[voter_id]["activated"])
                self.assertIsNone(rows[voter_id]["public_key"])

            output.clear()
            await self.seed.main()
            self.assertEqual(len(rows), 20)
            self.assertNotIn("fake-code", "\n".join(output))
            self.assertIn("Đã thêm 0 cử tri mới.", output)

    async def test_insert_error_does_not_print_uncommitted_code(self):
        rolled_back = False

        class FailingSession:
            async def execute(self, statement):
                raise RuntimeError("Lỗi DB giả")

        class FakeFactory:
            @staticmethod
            @asynccontextmanager
            async def begin():
                nonlocal rolled_back
                try:
                    yield FailingSession()
                except RuntimeError:
                    rolled_back = True
                    raise

        output = StringIO()
        with patch.object(self.seed, "AppSession", FakeFactory), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, "Lỗi DB giả"):
                await self.seed.main()

        self.assertTrue(rolled_back)
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
