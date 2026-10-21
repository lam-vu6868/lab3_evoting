"""
MỤC ĐÍCH: GET /results chỉ trả tổng kiểm phiếu cho JWT role admin.
PHỤ THUỘC: require_admin, TallySession, KMS nạp lúc startup và tally_votes.
LUỒNG: Xác minh role, mở session tally_user, kiểm thời gian ở service, trả ResultResponse.
TỰ KIỂM TRA: STAGE6_TEST_DB_NAME=... python -m unittest tests.test_tally -v.
"""

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ResultResponse
from app.auth.auth import require_admin
from app.core.config import get_settings
from app.crypto.kms import KMS
from app.database.database import TallySession
from app.voting.tally import TallyError, tally_votes
from app.voting.vote import get_kms


router = APIRouter()


async def get_tally_db() -> AsyncGenerator[AsyncSession, None]:
    async with TallySession() as session:
        yield session


@router.get("/results", response_model=ResultResponse)
async def results(
    admin_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_tally_db),
    kms: KMS = Depends(get_kms),
) -> ResultResponse:
    try:
        return await tally_votes(session, get_settings(), kms)
    except TallyError as error:
        raise HTTPException(error.status_code, error.detail) from error
