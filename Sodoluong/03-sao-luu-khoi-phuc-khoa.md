# 3. Tạo bản sao và khôi phục khóa riêng cử tri

**Ví dụ:** Sau khi kích hoạt `SV001`, cử tri bấm **Tải bản sao khóa riêng**. Nếu đổi thiết bị, cử tri mang file `SV001-private.pem` sang thiết bị mới để nhập lại. Đây là khóa ký của cử tri, khác private key của KMS dùng để mở khóa AES của phiếu.

## Tạo và tải bản sao

1. Lúc kích hoạt, `generateVoterKeys()` tạo cặp RSA-PSS 2048. `savePrivateKey()` xuất private key dạng PKCS8, đổi sang Base64 và lưu trong `localStorage` dưới khóa `voter_private_key:SV001`. Public key được lưu riêng ở `voter_public_key:SV001` và gửi cho backend trong `/activate`.
2. Nút tải ở `register.html` hoặc `vote.html` gọi `downloadPrivateKey("SV001")` trong `ui.js`. Hàm dùng `loadPrivateKey()` đọc khóa từ `localStorage`, rồi `exportPrivateKeyPem()` tạo văn bản PEM `BEGIN PRIVATE KEY`.
3. Trình duyệt tạo Blob và kích hoạt tải file tên `SV001-private.pem`. **Không có lời gọi API hoặc ghi DB trong bước tải.** Nếu thiết bị không có khóa riêng, trang báo lỗi thay vì tạo khóa mới.

## Nhập lại bản sao

1. Cử tri chọn file PKCS8 PEM trên trang kích hoạt hoặc trang bỏ phiếu. `importPrivateKeyPem()` kiểm tra cấu trúc PEM/Base64, nạp khóa RSA-PSS và yêu cầu RSA 2048, exponent 65537.
2. Giao diện chỉ gọi `savePrivateKey("SV001", key)` nếu chưa có khóa riêng cho `SV001` trên thiết bị; nó không tự ghi đè khóa đang có. Khóa được lưu lại vào `localStorage` của trình duyệt hiện tại. **Không có lời gọi API hoặc ghi DB khi nhập file.**
3. Khi bỏ phiếu, `signPayload()` dùng khóa vừa nhập để ký. Backend dùng `voters.public_key` của `SV001` để xác minh chữ ký. File nhập sai tài khoản có thể vượt qua bước kiểm tra định dạng ở trình duyệt, nhưng chữ ký sẽ bị từ chối khi gửi phiếu.

**Giới hạn quan trọng:** Code mới kiểm tra định dạng khóa lúc nhập, chưa đối chiếu cặp khóa với public key trên server ngay tại bước khôi phục. Luồng khôi phục trên thiết bị mới cũng chưa được kiểm chứng bằng test trình duyệt trong checkpoint hiện có. File PEM chứa private key không được mã hóa bằng mật khẩu; ai có file có thể ký thay cử tri. `localStorage` của bản demo cũng có rủi ro nếu trang bị XSS (mã độc chạy trong trình duyệt).

**Code:** [crypto.js](../static/js/crypto.js), [ui.js](../static/js/ui.js), [activate.js](../static/js/activate.js), [vote.js](../static/js/vote.js). **Kiểm tra liên quan:** [test_crypto.py](../tests/test_crypto.py); kiểm tra trình duyệt đã ghi ở [ROADMAP.md](../ROADMAP.md).
