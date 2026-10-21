<!--
MỤC ĐÍCH: Ghi giới hạn và rủi ro thực tế của bản demo bầu cử.
PHỤ THUỘC: app/, static/, db/init.sql, requirements.txt và docs/STRUCTURE.md.
LUỒNG: Đối chiếu dữ liệu browser, backend, DB và KMS để nhận diện nơi còn tin cậy.
TỰ KIỂM TRA: Mỗi kết luận đối chiếu code/test; không suy ra an toàn vận hành từ test demo.
-->

# Giới hạn và rủi ro của bản demo

Hệ thống đã có kiểm tra chữ ký, mã hóa phiếu, khóa dòng và phân quyền DB.
Những kiểm tra đó xác nhận các trường hợp đã thử, chưa đủ để dùng cho bầu cử thật.

| Rủi ro | Thực tế trong code | Hệ quả / việc cần làm trước sử dụng thật |
| --- | --- | --- |
| Backend biết lựa chọn | `/vote` nhận `ballot.candidate_id` trước khi mã hóa | Người kiểm soát backend có thể biết lựa chọn; cần thiết kế giao thức khác nếu yêu cầu kín phiếu với server |
| KMS cùng backend | `app/main.py` nạp khóa từ `KMS_KEY_DIR`; `tally.py` gọi giải mã | Người có quyền trên backend hoặc thư mục khóa có thể đọc phiếu; cần cô lập khóa, kiểm soát truy cập và sao lưu an toàn |
| Liên kết gián tiếp | `votes` không có `voter_id`, nhưng envelope sau giải mã có nonce, thời gian và chữ ký ballot; `voter_status` giữ chữ ký cast | Dữ liệu bổ sung hoặc log có thể giúp nối danh tính với phiếu; tách bảng không bảo đảm ẩn danh tuyệt đối |
| Khóa cử tri ở browser | `crypto.js` lưu khóa demo trong browser, trang cho tải/nhập PKCS8 | XSS hoặc người dùng làm lộ file backup có thể lấy khóa; mất cả khóa lẫn backup thì không có cơ chế khôi phục tự động; nhập backup trên thiết bị mới chưa được kiểm chứng |
| Receipt hạn chế | Receipt là hash của `sig_cast`; DB không giữ đủ cast payload để người ngoài kiểm chứng độc lập | Receipt không phải bằng chứng kiểm phiếu đầu cuối và không chứng minh lựa chọn đã được đếm |
| Kiểm phiếu phụ thuộc mọi phiếu | `tally.py` dừng nếu một phiếu không giải mã hoặc sai định dạng | Một phiếu lỗi có thể khiến API kết quả trả lỗi; cần quy trình xử lý, đối soát và giám sát có kiểm chứng |
| Vận hành chưa hoàn thiện | Chưa có rate limit, TLS triển khai, giám sát bảo mật hay quy trình xoay khóa | Có nguy cơ dò mật khẩu, chặn/nghe lén lưu lượng hoặc không phát hiện sự cố; chỉ chạy trong môi trường demo tin cậy |
| Thư viện ghim cũ | `requirements.txt` giữ phiên bản từ giai đoạn đầu | Chưa rà soát lỗ hổng và tương thích để triển khai thực tế |

Python không bảo đảm xóa sạch plaintext và DEK khỏi bộ nhớ sau khi dùng.
KMS demo lưu private key dạng PEM trên đĩa; tuyệt đối không đưa khóa, `.env`, JWT,
mã kích hoạt thật hoặc nội dung phiếu vào Git/log. Không tạo lại private key KMS
đang dùng: phiếu cũ có thể mất khả năng giải mã.

Test hiện có dùng dữ liệu giả và DB thử nghiệm riêng. Replay, chữ ký sai, mốc thời gian,
phân quyền và rollback đã được kiểm tra trong phạm vi nêu ở [ROADMAP.md](../ROADMAP.md);
chưa có kiểm toán độc lập, kiểm thử tải/tấn công toàn diện hoặc đánh giá bảo mật để triển khai thật.
