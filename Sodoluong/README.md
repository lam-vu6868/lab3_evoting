# Sơ đồ luồng của bản demo bầu cử

Đọc theo thứ tự dưới đây để theo một ví dụ xuyên suốt: cử tri giả `SV001` được cấp mã kích hoạt, chọn ứng viên có `candidate_id = 2`, rồi quản trị viên xem tổng sau khi kết thúc. Mã kích hoạt, mật khẩu, chữ ký và khóa riêng trong tài liệu chỉ được gọi bằng tên; không có giá trị bí mật thật.

| Thứ tự | File | Câu hỏi được trả lời |
| --- | --- | --- |
| 0 | [00-khoi-dong-he-thong.md](00-khoi-dong-he-thong.md) | PostgreSQL, quyền DB và khóa KMS được chuẩn bị ra sao? |
| 1 | [01-chuan-bi-cu-tri.md](01-chuan-bi-cu-tri.md) | Tài khoản và mã kích hoạt xuất hiện từ đâu? |
| 2 | [02-kich-hoat.md](02-kich-hoat.md) | “Đăng ký” trong demo kiểm tra và ghi gì? |
| 3 | [03-sao-luu-khoi-phuc-khoa.md](03-sao-luu-khoi-phuc-khoa.md) | Tạo, tải và nhập lại bản sao khóa riêng thế nào? |
| 4 | [04-dang-nhap.md](04-dang-nhap.md) | Mật khẩu được kiểm tra ra sao, JWT được cấp ở đâu? |
| 5 | [05-xem-ung-vien.md](05-xem-ung-vien.md) | Danh sách ứng viên đến từ bảng nào? |
| 6 | [06-bo-phieu.md](06-bo-phieu.md) | Hai chữ ký, mã hóa, transaction và biên nhận hoạt động thế nào? |
| 7 | [07-dang-nhap-admin-va-kiem-phieu.md](07-dang-nhap-admin-va-kiem-phieu.md) | Admin đăng nhập và nhận tổng phiếu thế nào? |
| 8 | [08-cap-lai-ma-kich-hoat.md](08-cap-lai-ma-kich-hoat.md) | Mã kích hoạt của tài khoản chưa kích hoạt được cấp lại thế nào? |

**Thuật ngữ:** `JWT` là mã xác thực được gửi cùng các yêu cầu cần quyền; `nonce` là số ngẫu nhiên dùng một lần để chặn gửi lại phiếu; `transaction` là nhóm thay đổi DB cùng thành công hoặc cùng hủy; `KMS` ở đây là bộ quản lý khóa mô phỏng nằm trong backend.

Các file này mô tả code hiện có, không phải hướng dẫn vận hành bầu cử thật. Backend thấy lựa chọn trước khi mã hóa; KMS nằm trong backend; tách bảng không bảo đảm ẩn danh tuyệt đối. Hợp đồng dữ liệu chuẩn ở [docs/STRUCTURE.md](../docs/STRUCTURE.md).
