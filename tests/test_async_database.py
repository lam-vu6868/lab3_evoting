"""
FILE: tests/test_async_database.py
MỤC ĐÍCH: Kiểm tra cấu hình SQLAlchemy async mà không mở kết nối PostgreSQL.
PHỤ THUỘC: unittest; app.database.database; biến môi trường giả, không dùng secret thật.
LUỒNG KIỂM TRA: import module với URL asyncpg, kiểm tra engine/session và vòng đời get_db().
CÁCH CHẠY: python -m unittest tests.test_async_database -v từ thư mục gốc.
"""
import importlib
import os
import sys
import unittest
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import get_settings


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


class AsyncDatabaseTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.env_patch = patch.dict(os.environ, TEST_ENV)
        cls.env_patch.start()
        cls.addClassCleanup(cls.env_patch.stop)

        get_settings.cache_clear()
        cls.addClassCleanup(get_settings.cache_clear)
        sys.modules.pop("app.database.database", None)
        cls.addClassCleanup(sys.modules.pop, "app.database.database", None)
        cls.database = importlib.import_module("app.database.database")

    def test_three_engines_use_asyncpg(self):
        for engine in (
            self.database.app_engine,
            self.database.admin_engine,
            self.database.tally_engine,
        ):
            with self.subTest(engine=engine):
                self.assertIsInstance(engine, AsyncEngine)
                self.assertEqual(engine.url.drivername, "postgresql+asyncpg")

    async def test_three_factories_create_async_sessions(self):
        for session_factory in (
            self.database.AppSession,
            self.database.AdminSession,
            self.database.TallySession,
        ):
            with self.subTest(session_factory=session_factory):
                session = session_factory()
                self.assertIsInstance(session, AsyncSession)
                await session.close()

    async def test_get_db_closes_session(self):
        class FakeSession:
            closed = False

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                self.closed = True

        fake_session = FakeSession()

        with patch.object(self.database, "AppSession", return_value=fake_session):
            dependency = self.database.get_db()
            self.assertIs(await anext(dependency), fake_session)
            await dependency.aclose()

        self.assertTrue(fake_session.closed)


if __name__ == "__main__":
    unittest.main()
