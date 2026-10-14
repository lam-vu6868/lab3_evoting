"""
FILE: app/core/config.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Đọc cấu hình một lần, cung cấp Settings cho các module.
PHỤ THUỘC: .env hoặc biến môi trường máy chạy backend; pydantic-settings.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo Settings và get_settings(); đọc .env khi chạy local, ưu tiên biến môi trường.
   Hiện chỉ PostgreSQL ở Docker: 3 DB URL dùng 127.0.0.1:5432/evoting;
   KMS_KEY_DIR dùng ./kms_keys. Docker Compose không truyền config cho backend local.
2. Khai báo JWT_SECRET, DATABASE_URL, ADMIN_DATABASE_URL, TALLY_DATABASE_URL,
   ADMIN_USERNAME, ADMIN_PASSWORD, KMS_KEY_DIR, ELECTION_ID, ELECTION_START, ELECTION_END.
3. Thêm tham số JWT hết hạn, PBKDF2 iterations, cửa sổ request 300 giây.
4. Parse thời gian có múi giờ; yêu cầu START < END; ELECTION_ID không rỗng.
5. Báo thiếu cấu hình bằng tên trường, không in secret/URL có mật khẩu.
6. Không tạo kết nối DB và không sinh khóa trong module cấu hình.

TỰ KIỂM TRA:
Cấu hình thiếu phải lỗi rõ; thời gian thiếu múi giờ phải bị từ chối; secret không xuất hiện trong log.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
