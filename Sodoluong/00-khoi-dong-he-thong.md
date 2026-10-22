# 0. Khởi tạo DB và khởi động backend

**Ví dụ:** Trước khi `SV001` kích hoạt, PostgreSQL cần có bảng `voters` và các bảng còn lại; backend cần nạp đúng khóa KMS để sau này giải mã phiếu đã lưu.

1. `docker-compose.yml` chỉ chạy PostgreSQL trong Docker, xuất cổng `127.0.0.1:5433` và giữ dữ liệu trong volume `pgdata`. Khi volume **mới**, entrypoint chạy `db/01_roles.sh` trước `db/init.sql`.
2. `01_roles.sh` tạo ba role DB: `app_user` cho luồng cử tri và ghi phiếu, `admin_app` chỉ đọc ứng viên theo quyền SQL hiện tại, `tally_user` đọc ứng viên và phiếu mã hóa để kiểm phiếu. `init.sql` tạo năm bảng `voters`, `candidates`, `votes`, `voter_status`, `used_nonces`, thêm ứng viên mẫu và cấp quyền từng bảng. Các script init không tự chạy lại chỉ vì backend khởi động lại trên volume cũ.
3. Backend chạy local từ `app/main.py`; `app/database/database.py` đọc ba URL kết nối từ cấu hình và tạo session theo role. Các route cử tri dùng `get_db()`/`app_user`; `/results` dùng `TallySession`/`tally_user`. `POST /admin/login` đối chiếu cấu hình ứng dụng, không dùng `admin_app` để đọc phiếu.
4. Khi backend startup, `lifespan()` gọi `KMS(...).ensure_keys()` theo `KMS_KEY_DIR`. KMS mô phỏng tạo cặp RSA-OAEP lúc đầu hoặc nạp lại private key đã có. Nếu còn public key nhưng mất private key, startup báo lỗi thay vì tự tạo khóa mới; khóa mới sẽ không mở được khóa AES của phiếu cũ. Khi backend dừng, ba engine DB được đóng.

**Phân biệt:** Cặp RSA KMS ở backend dùng để bọc/mở khóa AES của phiếu. Cặp RSA-PSS của `SV001` được tạo sau trong trình duyệt để ký. Không xóa volume DB hoặc tạo lại khóa KMS chỉ để thử luồng này.

**Code:** [docker-compose.yml](../docker-compose.yml), [01_roles.sh](../db/01_roles.sh), [init.sql](../db/init.sql), [main.py](../app/main.py), [database.py](../app/database/database.py), [kms.py](../app/crypto/kms.py). **Kiểm tra liên quan:** [test_database_setup.py](../tests/test_database_setup.py), [test_crypto.py](../tests/test_crypto.py).
