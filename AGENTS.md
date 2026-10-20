# Hướng dẫn làm việc trong dự án bầu cử

Áp dụng cho toàn bộ repository. Đây là nơi lưu quy tắc làm việc lâu dài, không phải bản ghi hội thoại. Yêu cầu cụ thể mới nhất của người dùng được ưu tiên khi thay đổi các quy ước dưới đây.

## Giao tiếp và cách học

- Trao đổi bằng tiếng Việt, dễ hiểu cho người mới học. Giải thích thuật ngữ khi xuất hiện lần đầu.
- Khi giải thích luồng, dùng một ví dụ xuyên suốt: dữ liệu được tạo ở đâu, hàm nào nhận, kiểm tra gì, ghi bảng/cột nào, trả kết quả gì.
- Khi người dùng hỏi cách viết code hoặc xin code mẫu, trình bày trong chat; không tự sửa file nếu chỉ đang hỏi kiến thức. Khi người dùng yêu cầu tạo/sửa file, thực hiện trong phạm vi đã yêu cầu, không hỏi xác nhận lại cho các bước thông thường.
- Làm từng chặng theo ROADMAP.md và phần người dùng đang học. Không tự triển khai toàn bộ các chặng còn lại.
- Ưu tiên code rõ ràng, tên dễ hiểu, ít tầng trung gian. Không giảm kiểm tra bảo mật để làm code ngắn hơn.
- Khi tạo hoặc sửa đáng kể file mã nguồn, giữ/cập nhật comment hoặc docstring đầu file: mục đích, phụ thuộc, luồng xử lý và cách tự kiểm tra. Không thêm comment vào định dạng không hỗ trợ comment hay file sinh tự động.

## Đọc tài liệu và xác định trạng thái

- Bắt đầu bằng README.md, ROADMAP.md và docs/STRUCTURE.md; sau đó đọc file liên quan tới yêu cầu.
- Tra hợp đồng payload, chữ ký, mã hóa và transaction trong docs/STRUCTURE.md. Tra ví dụ luồng trong docs/Luong_du_lieu_he_thong_bau_cu.md.
- Kiểm tra code thực tế trước khi kết luận tính năng đã có. File chỉ chứa hướng dẫn/docstring chưa phải tính năng đã triển khai.
- Tiến độ đặt trong ROADMAP.md, trạng thái tổng quan trong README.md, kiến trúc trong docs/. Cập nhật khi thay đổi liên quan đã được kiểm chứng; không đánh dấu hoàn thành chỉ vì tạo khung file.
- Nếu tài liệu và code mâu thuẫn, chỉ rõ điểm lệch và xử lý trong phạm vi công việc hiện tại; không tự thay đổi thiết kế lớn.

## Cấu trúc và môi trường

- Giữ cấu trúc hiện tại: app/ (backend), static/ (frontend), db/ (SQL và khởi tạo), tests/, docs/. Không tự chuyển sang ba thư mục BE/FE/DB.
- Backend gom theo chức năng trong app/core, auth, api, database, crypto, voting; app/main.py là điểm vào.
- Docker hiện chỉ chạy PostgreSQL qua docker-compose.yml. Không tự thêm build/container frontend hoặc backend.
- Backend chạy local. Kết nối DB local hiện dùng 127.0.0.1:5433; đối chiếu cấu hình thực tế trước khi chạy, không tự đổi cổng hoặc mật khẩu.
- Chạy lệnh Python từ thư mục gốc, ưu tiên môi trường venv của dự án nếu có. Không sửa thư viện bên trong venv/.
- Giữ LF cho script .sh chạy trong container. Không tự nâng dependency ngoài phạm vi yêu cầu.

## Giữ thiết kế và bảo vệ dữ liệu

- Giữ thiết kế năm bảng, ba role DB, hai chữ ký, AES-GCM và RSA-OAEP theo docs/STRUCTURE.md, trừ khi người dùng yêu cầu thay đổi.
- Phân biệt khóa cử tri với khóa KMS: private key cử tri ở phía cử tri; private key KMS mở khóa AES của phiếu. Không đưa private key vào response hoặc log.
- Dùng role DB đúng nhiệm vụ; không dùng postgres cho nghiệp vụ ứng dụng để né lỗi phân quyền.
- Đăng nhập chỉ đọc thông tin tài khoản và cấp JWT. Thao tác bỏ phiếu ghi nonce, phiếu và trạng thái trong cùng transaction, có khóa dòng chống bỏ phiếu đồng thời; chỉ trả thành công sau commit.
- Không tự thêm liên kết trực tiếp giữa danh tính cử tri và bảng votes hoặc trả phiếu đã giải mã cho admin. Kết quả kiểm phiếu chỉ trả tổng theo thiết kế.
- Không in hoặc đưa vào Git giá trị bí mật trong .env, mật khẩu, JWT, mã kích hoạt thật hoặc khóa riêng. Khi cần kiểm tra cấu hình, chỉ báo tên biến thiếu/hợp lệ hoặc giá trị đã che.
- Không ghi đè .env đang dùng bằng .env.example. Mẫu cấu hình chỉ chứa giá trị minh họa; bảo toàn giá trị người dùng đã đặt khi sửa biến khác.
- Không xóa volume PostgreSQL, reset DB, xóa dữ liệu hay tạo lại khóa KMS đang dùng nếu chưa có yêu cầu rõ ràng. Khởi tạo lại khóa có thể làm mất khả năng giải mã phiếu cũ.
- Dùng dữ liệu giả và môi trường riêng cho thử nghiệm ghi phiếu, phá dữ liệu hoặc kiểm tra tấn công.
- Nêu đúng giới hạn của bản demo: backend thấy lựa chọn trước mã hóa, KMS mô phỏng trong backend, tách bảng không đảm bảo ẩn danh tuyệt đối.

## Kiểm tra và báo cáo

- Chạy kiểm tra phù hợp với thay đổi. Sửa tài liệu đơn thuần chỉ cần rà nội dung và diff, không cần khởi động DB hay viết test mới.
- Kiểm tra khởi tạo/phân quyền DB hiện có: `python -m unittest tests.test_database_setup -v` khi Docker hoạt động; đọc test trước khi chạy nếu chưa biết tác động.
- Kiểm tra khóa dòng và transaction phải dùng PostgreSQL; SQLite không thay thế được kiểm tra đồng thời của thiết kế này.
- Không coi chạy thành công với 0 test là bằng chứng chức năng đúng.
- Báo ngắn gọn: đã đổi gì, đã kiểm tra gì, còn gì chưa kiểm chứng. Không nói ứng dụng chạy hoàn chỉnh nếu mới có khung hoặc chỉ kiểm tra một phần.

## MCP và ngữ cảnh giữa các cuộc chat

- Khi công cụ khả dụng và phù hợp: dùng Context7 tra tài liệu thư viện; dùng Playwright kiểm tra giao diện và hành vi trình duyệt.
- Nếu Codebase Memory MCP đã được kết nối và lập chỉ mục cho dự án, dùng để tra hàm, quan hệ gọi và phụ thuộc; đối chiếu với code hiện tại trước khi sửa. Không giả định công cụ đã cài, chỉ mục luôn mới hoặc bản đồ phản ánh toàn bộ hành vi lúc chạy.
- Kết quả MCP cũng chiếm ngữ cảnh; truy vấn tập trung vào vấn đề, tránh lấy dữ liệu thừa hoặc đưa bí mật vào truy vấn.
- Không đưa snapshot/log tạm của Playwright trong .playwright-mcp/ vào Git. Không tự xóa bằng chứng kiểm tra người dùng cần giữ.
- Không hứa nhớ toàn bộ hội thoại. Lưu quy tắc bền vững ở file này và tiến độ đã xác minh trong ROADMAP.md để cuộc chat sau có thể đọc lại.

## Bắt đầu một phiên chat mới

Khi người dùng nhắn `Tiếp tục dự án theo AGENTS.md`, thực hiện theo thứ tự sau:

1. Đọc `README.md`, `ROADMAP.md` và `docs/STRUCTURE.md` trước khi kết luận trạng thái dự án.
2. Kiểm tra code và test thực tế của chặng đang làm; không suy ra tiến độ chỉ từ tên file hoặc khung hướng dẫn.
3. Báo ngắn gọn chặng đã hoàn thành, chặng kế tiếp và phần chưa kiểm chứng.
4. Chỉ thực hiện chặng hoặc nhiệm vụ người dùng đang yêu cầu. Nếu người dùng chỉ hỏi kiến thức, giải thích trong chat và không sửa file.
5. Sau khi sửa code, chạy kiểm tra phù hợp; chỉ cập nhật `ROADMAP.md` và `README.md` khi kết quả đã được kiểm chứng.

Chọn công cụ theo công việc, người dùng không cần nhắc tên công cụ trong mọi yêu cầu:

- Ponytail đang bật để ưu tiên thay đổi nhỏ, rõ ràng và tránh tạo thêm tầng không cần thiết.
- Agent Skills hỗ trợ chọn quy trình lập kế hoạch, triển khai, gỡ lỗi, kiểm thử, review hoặc bảo mật phù hợp.
- Context7 dùng để tra tài liệu thư viện hiện hành trước khi dựa vào API hoặc cấu hình có thể đã thay đổi.
- Playwright dùng khi cần kiểm tra giao diện hoặc luồng trình duyệt đang chạy; dùng dữ liệu thử và không lưu snapshot/log tạm vào Git.
- Graphify dùng khi cần lập bản đồ kiến trúc, quan hệ file/hàm hoặc truy vấn một codebase lớn. Nếu đã có `graphify-out/`, kiểm tra độ mới và đối chiếu với code trước khi kết luận.


Câu mở đầu gợi ý cho chat mới:

```text
Tiếp tục dự án theo AGENTS.md. Đọc README.md, ROADMAP.md và docs/STRUCTURE.md,
kiểm tra code thực tế rồi cho tôi biết chặng hiện tại. Chưa sửa file cho đến khi xác định xong phạm vi.
```
