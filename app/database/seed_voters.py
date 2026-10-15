"""
FILE: app/database/seed_voters.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Nạp cử tri đủ điều kiện và cấp mã kích hoạt một lần; không tạo khóa RSA cử tri.
PHỤ THUỘC: app.database.database.AppSession; models.Voter; auth hash mã kích hoạt; asyncio.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo async main(); guard dùng asyncio.run(main()) khi chạy python -m app.database.seed_voters.
2. Danh sách 10 cử tri mẫu: voter_id/full_name; không nhận đăng ký công khai tùy ý.
3. Với cử tri chưa tồn tại, secrets.token_urlsafe(32) tạo activation_code.
4. INSERT voters: activation_hash, activated=false; password_hash/salt/public_key=NULL.
5. Commit thành công rồi mới xuất mã cấp cho người vận hành trong thao tác seed chủ động.
   Không log mã vào log web; không commit danh sách mã vào Git.
6. Chạy lại bỏ qua cử tri đã tồn tại, không reset người đã kích hoạt/bầu.
7. voter_status tạo lúc activate, không tạo phiếu tại seed.

TỰ KIỂM TRA:
Chạy hai lần không nhân đôi, không đổi dữ liệu cũ; DB không chứa activation code nguyên bản.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
