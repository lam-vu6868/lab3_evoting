<!--
FILE: docs/architecture.md
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Mô tả các thành phần, đường dữ liệu và ranh giới quyền.
PHỤ THUỘC: Source sau khi triển khai; ROADMAP.md; db/init.sql.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Vẽ browser → main → voting_service → DB; tally → crypto → KMS.
2. Liệt kê 5 bảng và 3 role.
3. Ghi rõ backend thấy lựa chọn trước mã hóa; KMS chạy cùng process không cách ly khỏi chủ máy.

TỰ KIỂM TRA:
Mỗi tuyên bố có đối chiếu code/test; không mô tả tính năng chưa làm như đã hoàn thành.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
-->
