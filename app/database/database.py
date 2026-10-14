"""
FILE: app/database/database.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Tạo ba kết nối PostgreSQL theo ba role, quản lý vòng đời session.
PHỤ THUỘC: app/core/config.py; SQLAlchemy; db/init.sql.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Khai báo Base (DeclarativeBase), ba engine từ ba DATABASE_URL riêng.
2. Tạo AppSession, AdminSession, TallySession tương ứng; không dùng tài khoản postgres.
3. get_db() yield AppSession và đóng trong finally; dependency không tự commit.
4. Tally nhận TallySession qua caller; không dùng AppSession đọc votes.
5. Quyền sở hữu transaction: caller mở with session.begin() trước các truy vấn của thao tác;
   voting_service không tự begin một transaction đã được SQLAlchemy autobegin.
6. Không Base.metadata.create_all() bằng app_user; schema do SQL init tạo.
7. Tắt echo SQL để tránh log payload; không in connection string có mật khẩu.

TỰ KIỂM TRA:
Session đóng kể cả khi lỗi; app_user INSERT được votes nhưng SELECT bị từ chối; tally_user chỉ đọc.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
