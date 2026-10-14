"""
FILE: tests/test_crypto.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Test hàm mật mã và xác thực, không cần PostgreSQL.
PHỤ THUỘC: unittest, tempfile; kms, crypto_service, signature_service, auth.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Viết unittest.TestCase; dùng TemporaryDirectory cho KMS, không dùng volume khóa thật.
2. Test AES round-trip, sửa ciphertext/tag/IV/wrapped key; restart KMS dùng cùng khóa.
3. Sinh khóa cử tri tạm trong test, ký RSA-PSS salt 32 rồi verify; đổi candidate/nonce/ts.
4. Có vector JSON/chữ ký cố định xuất từ WebCrypto để kiểm tương thích JS/Python.
5. Test password salt khác nhau, verify đúng/sai; JWT hết hạn/sai role/sửa chữ ký.
6. Guard unittest.main() để chạy python -m unittest tests.test_crypto.

TỰ KIỂM TRA:
Không có khóa thật trong fixture/Git; từng test xác minh hành vi, không chỉ mock mọi hàm để luôn pass.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
