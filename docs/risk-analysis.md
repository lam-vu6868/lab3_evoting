<!--
FILE: docs/risk-analysis.md
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Ghi giới hạn bảo mật thực tế của demo, không khẳng định an toàn tuyệt đối.
PHỤ THUỘC: Source sau khi triển khai; ROADMAP.md; db/init.sql.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. KMS/DB credentials cùng backend; chủ backend có thể đọc phiếu.
2. Private key localStorage có rủi ro XSS; mất khóa và phương án backup.
3. Sau giải mã, ballot chứa nonce/ts/chữ ký có thể hỗ trợ liên kết danh tính nếu có thêm dữ liệu.
4. sig_cast lưu riêng nhưng chưa lưu đủ cast payload để tự kiểm chứng độc lập về sau.
5. Chưa có bằng chứng kiểm phiếu đầu-cuối, rate limit, TLS triển khai hay xóa bộ nhớ bảo đảm.
6. Không gọi phiên bản dependency đang ghim là đã được đánh giá an toàn.

TỰ KIỂM TRA:
Mỗi tuyên bố có đối chiếu code/test; không mô tả tính năng chưa làm như đã hoàn thành.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
-->
