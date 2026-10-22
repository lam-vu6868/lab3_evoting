# Xem bảng và xóa dữ liệu demo trong PostgreSQL (Windows CMD)

Các lệnh dưới đây thao tác với database **`evoting`** trong Docker. Phần xóa làm mất toàn bộ cử tri, trạng thái bỏ phiếu, phiếu bầu, nonce và ứng viên trong 5 bảng; không thể lấy lại nếu chưa sao lưu. Chỉ dùng khi bạn muốn bắt đầu lại dữ liệu demo. Dừng backend và Cloudflare Tunnel trước khi xóa để không có người đang kích hoạt/bỏ phiếu.

Lệnh `TRUNCATE` ở đây **giữ nguyên bảng, quyền DB, Docker volume, `.env` và thư mục `kms_keys`**. Không chạy `docker compose down -v`.

## 1. Mở PostgreSQL

Chạy trong **CMD** tại thư mục dự án:

```cmd
cd /d D:\HeThongBauCu
docker compose up -d
```

Tất cả lệnh bên dưới chạy **trực tiếp tại dấu nhắc CMD `D:\HeThongBauCu>`**; không cần vào màn hình `evoting=#`. Đây là thao tác bảo trì DB bằng `postgres`; backend vẫn dùng các role riêng như trước.

## 2. Xem các bảng và dữ liệu cần kiểm tra

Mỗi dòng dưới đây là **một lệnh CMD riêng**. Chạy dòng nào bạn cần xem:

```cmd
docker compose exec postgres psql -U postgres -d evoting -c "\dt"
docker compose exec postgres psql -U postgres -d evoting -c "\d voters"
docker compose exec postgres psql -U postgres -d evoting -c "\d candidates"
docker compose exec postgres psql -U postgres -d evoting -c "\d votes"
docker compose exec postgres psql -U postgres -d evoting -c "\d voter_status"
docker compose exec postgres psql -U postgres -d evoting -c "\d used_nonces"
docker compose exec postgres psql -U postgres -d evoting -c "SELECT voter_id, full_name, activated FROM voters ORDER BY voter_id;"
docker compose exec postgres psql -U postgres -d evoting -c "SELECT candidate_id, name, party FROM candidates ORDER BY candidate_id;"
docker compose exec postgres psql -U postgres -d evoting -c "SELECT voter_id, has_voted FROM voter_status ORDER BY voter_id;"
docker compose exec postgres psql -U postgres -d evoting -c "SELECT COUNT(*) AS so_phieu FROM votes;"
docker compose exec postgres psql -U postgres -d evoting -c "SELECT COUNT(*) AS so_nonce FROM used_nonces;"
```

Năm bảng của dự án là `voters`, `candidates`, `votes`, `voter_status`, `used_nonces`. Chỉ xem số phiếu/nonce; không cần in dữ liệu mã hóa, hash hay khóa ra terminal.

## 3. Xóa toàn bộ dữ liệu trong 5 bảng

**Chỉ chạy khi chắc chắn muốn xóa mọi dữ liệu demo trong `evoting`.** Tại dấu nhắc `(venv) D:\HeThongBauCu>` hoặc `D:\HeThongBauCu>`, dán **nguyên dòng lệnh** sau, không dán hàng rào Markdown:

```cmd
docker compose exec postgres psql -U postgres -d evoting -v ON_ERROR_STOP=1 -c "BEGIN; TRUNCATE TABLE voter_status, voters, votes, used_nonces, candidates RESTART IDENTITY; COMMIT;"
```

`BEGIN` và `COMMIT` gom thao tác thành một transaction. `RESTART IDENTITY` đưa bộ đếm `candidate_id` về đầu. Nếu lệnh báo lỗi, việc xóa không được commit; xem lỗi trước khi thử lại.

Kiểm tra lại ngay trong CMD:

```cmd
docker compose exec postgres psql -U postgres -d evoting -c "SELECT (SELECT COUNT(*) FROM voters) AS voters, (SELECT COUNT(*) FROM candidates) AS candidates, (SELECT COUNT(*) FROM votes) AS votes, (SELECT COUNT(*) FROM voter_status) AS voter_status, (SELECT COUNT(*) FROM used_nonces) AS used_nonces;"
```

Năm kết quả phải bằng `0`.

## 4. Nếu muốn nạp lại dữ liệu demo

Sau khi xóa, `db/init.sql` **không tự chạy lại** vì Docker volume vẫn tồn tại. Thêm lại ứng viên mẫu bằng một lệnh CMD:

```cmd
docker compose exec postgres psql -U postgres -d evoting -c "INSERT INTO candidates (name, party) VALUES ('Nguyễn Văn A', 'Đảng X'), ('Trần Thị B', 'Đảng Y'), ('Lê Văn C', 'Đảng Z');"
```

Sau đó, từ **CMD** trong thư mục dự án, chạy seed cử tri:

```cmd
venv\Scripts\activate
python -m app.database.seed_voters
```

Seed hiện tạo SV001–SV010 và SV0011–SV0020. Mã kích hoạt mới chỉ in một lần sau khi ghi DB thành công; hãy lưu riêng, không đưa vào Git hoặc chat. Chạy lại seed khi cử tri đã có sẽ không tạo mã mới; dùng `python -m app.database.reissue_activation_codes` nếu cần cấp lại mã cho tài khoản chưa kích hoạt.
