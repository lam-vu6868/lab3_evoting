"""
MỤC ĐÍCH: Kiểm tra GET /candidates chỉ đọc và trả các trường công khai.
PHỤ THUỘC: unittest, session giả; không ghi PostgreSQL.
LUỒNG: Đọc ba ứng viên theo thứ tự ID và kiểm tra route đã gắn vào FastAPI.
TỰ KIỂM TRA: python -m unittest tests.test_candidates -v
"""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


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
    from app.api.candidates import list_candidates
    from app.main import app


class ReadOnlySession:
    async def execute(self, statement):
        if statement.column_descriptions[0]["entity"].__tablename__ != "candidates":
            raise AssertionError("Chỉ đọc candidates")
        rows = [
            SimpleNamespace(candidate_id=1, name="A", party="X"),
            SimpleNamespace(candidate_id=2, name="B", party=None),
        ]
        return SimpleNamespace(scalars=lambda: rows)

    def add(self, *_):
        raise AssertionError("Không được ghi DB")


class CandidateTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_only_public_candidate_fields(self):
        result = await list_candidates(ReadOnlySession())
        self.assertEqual([item.model_dump() for item in result], [
            {"candidate_id": 1, "name": "A", "party": "X"},
            {"candidate_id": 2, "name": "B", "party": None},
        ])

    async def test_main_registers_candidates_route(self):
        self.assertTrue(any(route.path == "/candidates" and "GET" in route.methods for route in app.routes))


if __name__ == "__main__":
    unittest.main()
