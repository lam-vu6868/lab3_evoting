"""
FILE: app/database/seed_voters.py
TRẠNG THÁI: Đã có xử lý seed và test dùng session giả; chưa kiểm trên PostgreSQL thật.
MỤC ĐÍCH: Nạp cử tri đủ điều kiện và cấp mã kích hoạt một lần; không tạo khóa RSA cử tri.
PHỤ THUỘC: app.database.database.AppSession; models.Voter; auth hash mã kích hoạt; asyncio.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo async main(); guard dùng asyncio.run(main()) khi chạy python -m app.database.seed_voters.
2. Danh sách 10 cử tri mẫu: voter_id/full_name; không nhận đăng ký công khai tùy ý.
3. Mỗi lần thử INSERT, secrets.token_urlsafe(32) tạo activation_code; chỉ cấp mã nếu cử tri mới.
4. INSERT voters: activation_hash, activated=false; password_hash/salt/public_key=NULL.
5. Commit thành công rồi mới xuất mã cấp cho người vận hành trong thao tác seed chủ động.
   Không log mã vào log web; không commit danh sách mã vào Git.
6. ON CONFLICT DO NOTHING bỏ qua cử tri đã tồn tại và mã vừa tạo; không reset người đã kích hoạt/bầu.
7. voter_status tạo lúc activate, không tạo phiếu tại seed.

TỰ KIỂM TRA:
python -m unittest tests.test_seed_voters -v dùng session giả để kiểm tra chạy lại và lỗi trước commit.
Chạy hai lần trên DB test riêng: không nhân đôi, không đổi dữ liệu cũ; DB không chứa activation code nguyên bản.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

import asyncio
import secrets

from sqlalchemy.dialects.postgresql import insert

from app.auth.auth import hash_activation_code
from app.database.database import AppSession
from app.database.models import Voter


async def main() -> None:
    """Chỉ thêm cử tri chưa có và chỉ cấp mã sau khi transaction đã commit."""
    # Dữ liệu giả để học; không đưa danh tính cử tri thật vào mã nguồn.
    sample_voters = [
        (f"SV{number:03}", f"Cử tri mẫu {number:02}")
        for number in range(1, 11)
    ]
    issued_codes: list[tuple[str, str]] = []

    # begin() commit khi thành công và rollback toàn bộ nếu có lỗi.
    async with AppSession.begin() as session:
        for voter_id, full_name in sample_voters:
            code = secrets.token_urlsafe(32)
            statement = (
                insert(Voter)
                .inline()  # Không yêu cầu DB trả lại hàng vừa INSERT.
                .values(
                    voter_id=voter_id,
                    full_name=full_name,
                    activation_hash=hash_activation_code(code),
                    activated=False,
                    password_hash=None,
                    salt=None,
                    public_key=None,
                )
                # Giữ nguyên cử tri đã có, kể cả tài khoản đã kích hoạt.
                .on_conflict_do_nothing(index_elements=[Voter.voter_id])
            )
            result = await session.execute(statement)
            if result.rowcount == 1:
                issued_codes.append((voter_id, code))

    # Chỉ hiện mã sau khi commit thành công; không ghi mã vào log web hoặc Git.
    for voter_id, code in issued_codes:
        print(f"{voter_id}: {code}")
    print(f"Đã thêm {len(issued_codes)} cử tri mới.")


if __name__ == "__main__":
    asyncio.run(main())
