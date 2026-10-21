"""
MỤC ĐÍCH: Đăng nhập cử tri đã kích hoạt và cấp JWT cho cuộc bầu cử hiện tại.
PHỤ THUỘC: LoginRequest/TokenResponse; auth.py; get_db; Voter; get_settings.
LUỒNG: Đọc voters theo voter_id, kiểm tra trạng thái và mật khẩu, trả JWT + election_id;
không ghi DB và không tạo khóa cử tri.
TỰ KIỂM TRA: python -m unittest tests.test_login -v
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LoginRequest, TokenResponse
from app.auth.auth import create_jwt, verify_password
from app.core.config import get_settings
from app.database.database import get_db
from app.database.models import Voter


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Sai ID, trạng thái hoặc mật khẩu đều trả cùng một lỗi đăng nhập."""
    result = await session.execute(select(Voter).where(Voter.voter_id == request.voter_id))
    voter = result.scalar_one_or_none()
    if (voter is None or not voter.activated or
            not verify_password(request.password, voter.password_hash, voter.salt)):
        raise HTTPException(401, "Thông tin đăng nhập không hợp lệ")

    return TokenResponse(
        access_token=create_jwt(voter.voter_id, "voter"),
        election_id=get_settings().ELECTION_ID,
    )
