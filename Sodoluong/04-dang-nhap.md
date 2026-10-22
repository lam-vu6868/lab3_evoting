# 4. Đăng nhập cử tri và giữ phiên

**Ví dụ:** `SV001` đã kích hoạt, nhập mã cử tri và mật khẩu tại `/static/login.html`. Khóa riêng đã lưu trên thiết bị không tham gia bước đăng nhập; nó chỉ cần khi ký phiếu.

1. `static/js/login.js` gửi `POST /login` với `{"voter_id":"SV001","password":"<mật khẩu cử tri>"}`. `LoginRequest` kiểm tra định dạng mã cử tri và độ dài mật khẩu.
2. `app/auth/login.py:login()` dùng session DB của `app_user` đọc dòng `voters` theo `voter_id`. Hàm kiểm tra tài khoản tồn tại, `activated = true` và `verify_password()` khớp `voters.password_hash` cùng `voters.salt`.
3. Nếu một trong ba điều kiện sai, API trả 401 với cùng thông báo chung. Nếu đúng, `create_jwt("SV001", "voter")` cấp JWT có role cử tri; `TokenResponse` trả `access_token`, `token_type = bearer`, `election_id` từ cấu hình.
4. Trình duyệt lưu `voter_token`, `voter_id`, `election_id` trong `sessionStorage` của phiên tab và chuyển tới `/static/vote.html`. Mật khẩu được xóa khỏi form; không lưu vào storage. Route đăng nhập **chỉ đọc DB**, không tạo khóa và không đổi trạng thái bỏ phiếu.
5. Khi bấm đăng xuất ở trang bỏ phiếu, code xóa ba giá trị phiên này rồi chuyển về trang đăng nhập. Private key lưu ở `localStorage` vẫn còn trên thiết bị.

**JWT dùng để làm gì?** Ở `/vote`, `require_voter()` xác minh token và lấy `voter_id` từ đó. Server không nhận một `voter_id` tùy ý trong body bỏ phiếu. JWT admin có role khác nên không dùng thay token cử tri.

**Code:** [login.js](../static/js/login.js), [login.py](../app/auth/login.py), [auth.py](../app/auth/auth.py), [vote.js](../static/js/vote.js). **Kiểm tra:** [test_login.py](../tests/test_login.py), [test_crypto.py](../tests/test_crypto.py).
