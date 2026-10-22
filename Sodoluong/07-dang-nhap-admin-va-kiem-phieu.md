# 7. Đăng nhập quản trị viên và xem tổng kiểm phiếu

**Ví dụ:** Sau khi `SV001` đã bỏ phiếu cho B và cuộc bầu cử kết thúc, quản trị viên mở `/static/admin.html`. Kết quả mong đợi trong ví dụ một phiếu là B = 1, `total_votes = 1`.

## Đăng nhập admin

1. `static/js/admin.js` gửi `POST /admin/login` với username/password của quản trị viên. `app/auth/admin.py` gọi `verify_admin_credentials()` so sánh với cấu hình `ADMIN_USERNAME`/`ADMIN_PASSWORD`; luồng này **không đọc bảng `voters`** và không dùng cử tri làm admin.
2. Đúng thì `create_jwt(..., "admin")` cấp JWT role admin. Trang giữ `admin_token` riêng trong `sessionStorage`, xóa mật khẩu khỏi form và gọi `/results`. Sai thì API trả 401.

## Kiểm phiếu

1. `GET /results` nhận Bearer token. `require_admin()` kiểm role; token cử tri không có quyền xem kết quả.
2. `tally_votes()` kiểm thời điểm hiện tại đã qua `ELECTION_END`; trước đó trả 403 và chưa đọc phiếu. Route cấp session `tally_user`, role DB chỉ được đọc `votes` và `candidates`.
3. Service đọc ứng viên và phiếu đã mã hóa, trộn thứ tự phiếu trong RAM, rồi dùng private key **KMS** mở khóa AES và `decrypt_vote()` giải mã từng phiếu trong RAM. Service lấy `ballot.candidate_id`, kiểm đó là ứng viên có trong danh sách và tăng bộ đếm. Nếu có phiếu hỏng hoặc ứng viên không hợp lệ, toàn bộ lượt kiểm phiếu báo lỗi 500; không trả một tổng sai.
4. API chỉ trả `results` gồm `candidate_id`, `name`, `votes` và `total_votes`. Trang admin chỉ hiển thị bảng tổng; không nhận private key, phiếu giải mã hay danh tính cử tri. Luồng xem kết quả không ghi DB.
5. Bấm đăng xuất xóa `admin_token` khỏi `sessionStorage`.

**Phân biệt hai khóa:** private key cử tri chỉ ở thiết bị cử tri để ký; private key KMS ở backend dùng mở khóa AES của phiếu. Trong bản demo, KMS chưa tách thành dịch vụ độc lập.

**Code:** [admin.js](../static/js/admin.js), [admin.py](../app/auth/admin.py), [results.py](../app/voting/results.py), [tally.py](../app/voting/tally.py). **Kiểm tra:** [test_tally.py](../tests/test_tally.py), [test_attack.py](../tests/test_attack.py).
