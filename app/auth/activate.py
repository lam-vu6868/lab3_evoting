"""
MỤC ĐÍCH: Kích hoạt một cử tri đã được seed bằng mã dùng một lần và public key.
PHỤ THUỘC: ActivationRequest; auth.py; get_db; Voter/VoterStatus; kiểm tra khóa RSA.
LUỒNG: Khóa dòng voters, kiểm tra mã, lưu hash mật khẩu và public key, tạo voter_status
trong cùng transaction; chỉ trả thành công sau commit.
TỰ KIỂM TRA: python -m unittest tests.test_activate -v
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ActivationRequest
from app.auth.auth import hash_password, verify_activation_code
from app.crypto.signature_service import load_voter_public_key
from app.database.database import get_db
from app.database.models import Voter, VoterStatus


router = APIRouter()


@router.post("/activate")
async def activate(request: ActivationRequest, session: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    """Kích hoạt đúng một lần; lỗi giữa chừng rollback cả hai bảng."""
    try:
        load_voter_public_key(request.public_key)
    except ValueError as error:
        raise HTTPException(400, "Thông tin kích hoạt không hợp lệ") from error

    async with session.begin():
        result = await session.execute(
            select(Voter).where(Voter.voter_id == request.voter_id).with_for_update()
        )
        voter = result.scalar_one_or_none()
        if (voter is None or voter.activated or
                not verify_activation_code(request.activation_code, voter.activation_hash)):
            raise HTTPException(400, "Thông tin kích hoạt không hợp lệ")

        voter.password_hash, voter.salt = hash_password(request.password)
        voter.public_key = request.public_key
        voter.activation_hash = None
        voter.activated = True
        session.add(VoterStatus(voter_id=request.voter_id))

    return {"success": True}
