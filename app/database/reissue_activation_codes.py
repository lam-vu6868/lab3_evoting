"""Cấp lại mã kích hoạt cho các cử tri chưa kích hoạt, không xóa tài khoản.

Phụ thuộc: AppSession (app_user), Voter, secrets và hash_activation_code.
Luồng: khóa các dòng chưa kích hoạt, thay activation_hash trong một transaction;
chỉ in mã mới sau khi commit thành công. Mã cũ hết hiệu lực.
Tự kiểm tra: python -m unittest tests.test_reissue_activation_codes -v
Chạy thật từ gốc dự án: python -m app.database.reissue_activation_codes
"""

import asyncio
import secrets

from sqlalchemy import select

from app.auth.auth import hash_activation_code
from app.database.database import AppSession
from app.database.models import Voter


async def main() -> None:
    issued_codes: list[tuple[str, str]] = []

    async with AppSession.begin() as session:
        result = await session.execute(
            select(Voter)
            .where(Voter.activated.is_(False))
            .order_by(Voter.voter_id)
            .with_for_update()
        )
        for voter in result.scalars().all():
            code = secrets.token_urlsafe(32)
            voter.activation_hash = hash_activation_code(code)
            issued_codes.append((voter.voter_id, code))

    for voter_id, code in issued_codes:
        print(f"{voter_id}: {code}")
    print(f"Đã cấp lại mã cho {len(issued_codes)} cử tri chưa kích hoạt.")


if __name__ == "__main__":
    asyncio.run(main())
