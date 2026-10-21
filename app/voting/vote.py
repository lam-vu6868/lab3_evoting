"""
MỤC ĐÍCH: Route POST /vote nhận JWT cử tri và chỉ trả thành công sau commit.
PHỤ THUỘC: VoteRequest/VoteResponse, require_voter, get_db, KMS đã nạp khi startup,
voting_service và PostgreSQL app_user.
LUỒNG: Xác minh JWT bằng dependency; mở transaction; gọi cast_vote; sau commit trả receipt.
TỰ KIỂM TRA: STAGE5_TEST_DB_NAME=... python -m unittest tests.test_voting -v.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import VoteRequest, VoteResponse
from app.auth.auth import require_voter
from app.core.config import get_settings
from app.crypto.kms import KMS
from app.database.database import get_db
from app.voting.voting_service import VotingError, cast_vote


router = APIRouter()


def get_kms(request: Request) -> KMS:
    """Lấy KMS đã nạp lúc ứng dụng khởi động, không tạo lại khóa theo request."""
    return request.app.state.kms


@router.post("/vote", response_model=VoteResponse)
async def vote(
    request: VoteRequest,
    voter_id: str = Depends(require_voter),
    session: AsyncSession = Depends(get_db),
    kms: KMS = Depends(get_kms),
) -> VoteResponse:
    """Service không commit; lỗi trong begin sẽ rollback trước khi route xử lý."""
    try:
        async with session.begin():
            receipt = await cast_vote(session, voter_id, request, get_settings(), kms)
    except VotingError as error:
        raise HTTPException(error.status_code, error.detail) from error
    except IntegrityError as error:
        cause = error.orig
        while cause is not None:
            if (getattr(cause, "sqlstate", None) == "23505" and
                    getattr(cause, "constraint_name", None) == "used_nonces_pkey"):
                raise HTTPException(409, "Nonce đã được dùng") from error
            cause = cause.__cause__
        raise
    return VoteResponse(receipt=receipt)
