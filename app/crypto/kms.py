"""
FILE: app/crypto/kms.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Quản lý cặp RSA của hệ thống để bọc/mở khóa AES; khác khóa ký của cử tri.
PHỤ THUỘC: app/core/config.py; cryptography; thư mục KMS_KEY_DIR (local: ./kms_keys).

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo KMS(key_dir), ensure_keys(), wrap_dek(dek: bytes), unwrap_dek(wrapped: bytes).
2. ensure_keys chạy rõ ràng lúc startup: nếu chưa có cặp khóa thì sinh RSA 2048, exponent 65537.
3. Lưu PEM: private ở file riêng với quyền hạn chế, public ở file riêng.
   Tạo file an toàn/atomic; tránh hai tiến trình sinh hai cặp. Nếu thiếu/hỏng một file,
   báo lỗi hoặc khôi phục public từ private hợp lệ; không âm thầm thay private cũ.
4. wrap_dek chỉ cần public key; dùng OAEP với SHA-256, MGF1 SHA-256, label=None.
5. unwrap_dek chỉ nạp private khi cần; trả đúng 32 byte khóa AES hoặc báo lỗi.
6. Không có endpoint xuất khóa. Private vẫn được lưu trên volume, không phải chỉ tồn tại trong RAM.
7. Không coi class này là KMS độc lập: người kiểm soát backend/thư mục khóa vẫn có thể lấy khóa.

TỰ KIỂM TRA:
Wrap rồi unwrap khớp; restart dùng lại khóa; private sai không mở được; mất khóa không được tự thay để tiếp tục kiểm phiếu.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
