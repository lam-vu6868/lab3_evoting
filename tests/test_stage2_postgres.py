"""
MỤC ĐÍCH: Kiểm chứng checkpoint Chặng 2 bằng SQLAlchemy async và PostgreSQL thật.
PHỤ THUỘC: Docker PostgreSQL healthy; APP_DATABASE_URL và TALLY_DATABASE_URL trong .env.
LUỒNG: app_user đọc ứng viên, INSERT phiếu giả bằng Core inline, ROLLBACK,
rồi tally_user xác nhận phiếu giả không được lưu.
CÁCH CHẠY: python -m unittest tests.test_stage2_postgres -v
"""

import unittest
import uuid

from sqlalchemy import insert, select

from app.database.database import (
    AppSession,
    TallySession,
    app_engine,
    tally_engine,
)
from app.database.models import Candidate, Vote


class Stage2PostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        """Đóng pool để mỗi test không giữ kết nối sang event loop kế tiếp."""
        await app_engine.dispose()
        await tally_engine.dispose()

    async def test_app_user_reads_candidates_through_sqlalchemy(self):
        async with AppSession() as session:
            result = await session.execute(
                select(Candidate).order_by(Candidate.candidate_id)
            )
            candidates = result.scalars().all()

        self.assertEqual(len(candidates), 3)
        self.assertEqual([candidate.candidate_id for candidate in candidates], [1, 2, 3])

    async def test_inline_vote_insert_succeeds_then_rolls_back(self):
        vote_id = uuid.uuid4()
        statement = insert(Vote).inline().values(
            vote_id=vote_id,
            ciphertext=b"test-ciphertext",
            wrapped_dek=b"test-wrapped-dek",
            iv=b"0" * 12,
            tag=b"0" * 16,
        )

        async with AppSession() as session:
            transaction = await session.begin()
            try:
                await session.execute(statement)
            finally:
                await transaction.rollback()

        async with TallySession() as session:
            result = await session.execute(
                select(Vote.vote_id).where(Vote.vote_id == vote_id)
            )

        self.assertIsNone(result.scalar_one_or_none())


if __name__ == "__main__":
    unittest.main()
