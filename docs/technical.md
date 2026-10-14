<!--
FILE: docs/technical.md
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Giải thích giao thức ký, mã hóa và mapping từng trường dữ liệu.
PHỤ THUỘC: Source sau khi triển khai; ROADMAP.md; db/init.sql.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Mô tả JSON canonical, RSA-PSS SHA-256 salt 32, Base64.
2. Mô tả AES-GCM tag nối/tách, OAEP SHA-256, UUID v4.
3. Mô tả PBKDF2/salt/iterations, JWT claims, transaction và receipt.
4. Phân biệt thiết kế với tính năng đã kiểm thử.

TỰ KIỂM TRA:
Mỗi tuyên bố có đối chiếu code/test; không mô tả tính năng chưa làm như đã hoàn thành.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
-->
