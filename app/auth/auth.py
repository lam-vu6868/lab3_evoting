"""
FILE: app/auth/auth.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Băm mật khẩu, kiểm tra mã kích hoạt và cấp/xác minh JWT.
PHỤ THUỘC: app/core/config.py; cryptography PBKDF2HMAC; python-jose; không sinh khóa RSA.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Chốt PBKDF2-HMAC-SHA256 để tận dụng dependency hiện có và cột salt riêng.
   hash_password(password) trả (encoded_hash_bytes, salt_bytes); salt ngẫu nhiên cho từng tài khoản.
2. encoded_hash lưu phiên bản + iterations + digest; verify_password đọc tham số đã lưu,
   không lệ thuộc iterations cấu hình mới; so sánh constant-time. Hiệu chỉnh iterations trước sử dụng thật.
3. Mã kích hoạt do seed sinh đủ ngẫu nhiên: lưu SHA-256(code) trong activation_hash;
   không áp dụng SHA-256 đơn thuần cho mật khẩu người dùng.
4. create_jwt(subject, role) dùng secret riêng, thuật toán cố định HS256, sub/role/iat/exp.
5. verify_jwt bắt buộc exp, sub, role hợp lệ; allowlist HS256, không lấy thuật toán từ request.
6. Dependency lấy Bearer token; require_voter/require_admin kiểm tra đúng role.
7. Admin đối chiếu cấu hình bằng so sánh hằng thời gian; không lưu admin vào voters.
8. Login lấy voters ở main: activated=true rồi verify password. Sai trả lỗi chung, không log mật khẩu.

TỰ KIỂM TRA:
Cùng mật khẩu có salt khác; mật khẩu sai bị từ chối; JWT sửa/hết hạn/sai role đều bị chặn.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
