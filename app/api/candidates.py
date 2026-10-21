"""
MỤC ĐÍCH: Trả danh sách ứng viên công khai cho trình duyệt chọn phiếu.
PHỤ THUỘC: CandidateResponse, get_db và model Candidate; dùng role app_user.
LUỒNG: Đọc candidates theo candidate_id, chỉ trả ID, tên và đảng; không ghi DB.
TỰ KIỂM TRA: python -m unittest tests.test_candidates -v
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import CandidateResponse
from app.database.database import get_db
from app.database.models import Candidate


router = APIRouter()


@router.get("/candidates", response_model=list[CandidateResponse])
async def list_candidates(session: AsyncSession = Depends(get_db)) -> list[CandidateResponse]:
    """Đọc danh sách ứng viên theo ID ổn định, không trả dữ liệu bảng khác."""
    result = await session.execute(select(Candidate).order_by(Candidate.candidate_id))
    return [
        CandidateResponse(candidate_id=row.candidate_id, name=row.name, party=row.party)
        for row in result.scalars()
    ]
