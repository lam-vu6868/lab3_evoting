# 8. Cấp lại mã kích hoạt cho cử tri chưa kích hoạt

**Ví dụ:** `SV001` được seed nhưng chưa kích hoạt và làm mất mã ban đầu. Người vận hành chủ động chạy `python -m app.database.reissue_activation_codes` trên môi trường được chọn.

1. `app/database/reissue_activation_codes.py:main()` dùng `AppSession` của `app_user`, mở một transaction, đọc các dòng `voters` có `activated = false` theo `voter_id` và khóa chúng bằng `FOR UPDATE`.
2. Với mỗi cử tri chưa kích hoạt, script tạo mã ngẫu nhiên mới, băm bằng `hash_activation_code()`, rồi thay `voters.activation_hash`. Mã cũ hết hiệu lực. Script **không thay mật khẩu, public key hoặc dữ liệu cử tri đã kích hoạt**.
3. Sau commit, script mới in cặp `voter_id` và mã mới cho người vận hành. Đây là lệnh bảo trì, không phải API công khai. Mã gốc không được lưu trong DB; vì vậy cần cấp mã mới thay vì đọc lại mã cũ.

Lệnh này tác động tới **mọi** cử tri chưa kích hoạt trong DB được cấu hình, không chỉ `SV001`. Không chạy trên DB đang dùng nếu chưa chủ ý cấp lại toàn bộ các mã đó. Không đưa mã in ra vào Git hoặc log web.

**Code:** [reissue_activation_codes.py](../app/database/reissue_activation_codes.py), [auth.py](../app/auth/auth.py). **Kiểm tra:** [test_reissue_activation_codes.py](../tests/test_reissue_activation_codes.py).
