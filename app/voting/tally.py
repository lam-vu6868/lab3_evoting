"""
MỤC ĐÍCH: Sau giờ kết thúc, giải mã phiếu trong RAM và trả tổng theo ứng viên.
PHỤ THUỘC: TallySession do route cấp, Vote/Candidate, decrypt_vote, KMS và thời gian cấu hình.
LUỒNG: Chặn kiểm sớm; đọc ứng viên/phiếu; giải mã từng phiếu; lỗi bất kỳ phiếu nào dừng tổng.
TỰ KIỂM TRA: STAGE6_TEST_DB_NAME=... python -m unittest tests.test_tally -v.
"""

import json
from datetime import datetime, timezone
from random import shuffle

from cryptography.exceptions import InvalidTag
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ResultItem, ResultResponse
from app.crypto.crypto_service import decrypt_vote
from app.crypto.kms import KMS
from app.database.models import Candidate, Vote


class TallyError(ValueError):
    """Lỗi kiểm phiếu để route trả mã HTTP mà không lộ nội dung phiếu."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def tally_votes(session: AsyncSession, settings, kms: KMS) -> ResultResponse:
    """Đọc bằng tally_user; không lưu plaintext hoặc trả từng phiếu."""
    if datetime.now(timezone.utc) < settings.ELECTION_END:
        raise TallyError(403, "Chưa đến thời gian kiểm phiếu")

    candidates = (await session.execute(select(Candidate).order_by(Candidate.candidate_id))).scalars().all()
    counts = {candidate.candidate_id: 0 for candidate in candidates}
    votes = list((await session.execute(select(Vote))).scalars().all())
    shuffle(votes)

    for vote in votes:
        try:
            plaintext = decrypt_vote({
                "ciphertext": vote.ciphertext, "wrapped_dek": vote.wrapped_dek,
                "iv": vote.iv, "tag": vote.tag,
            }, kms)
            envelope = json.loads(plaintext)
            if not isinstance(envelope, dict) or not isinstance(envelope.get("ballot"), dict):
                raise ValueError("Envelope sai định dạng")
            candidate_id = envelope["ballot"].get("candidate_id")
            if type(candidate_id) is not int or candidate_id not in counts:
                raise ValueError("Ứng viên không hợp lệ")
        except (InvalidTag, UnicodeError, ValueError, TypeError, KeyError) as error:
            raise TallyError(500, "Không thể kiểm phiếu") from error
        counts[candidate_id] += 1

    return ResultResponse(
        results=[ResultItem(candidate_id=row.candidate_id, name=row.name, votes=counts[row.candidate_id])
                 for row in candidates],
        total_votes=sum(counts.values()),
    )
