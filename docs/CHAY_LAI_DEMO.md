# Chạy lại bản demo qua Cloudflare Tunnel (Windows CMD)

Thực hiện từ thư mục `D:\HeThongBauCu`. Không cần deploy: PostgreSQL chạy trong Docker, backend và giao diện chạy trên máy này, Cloudflare Tunnel cấp link HTTPS tạm để người khác truy cập qua Internet.

## 1. Bật PostgreSQL

Mở cửa sổ CMD thứ nhất:

```cmd
cd /d D:\HeThongBauCu
docker compose up -d
docker compose ps
```

Đợi `postgres` hiện `healthy`. Lệnh này dùng lại dữ liệu trong Docker volume hiện có; không cần nạp lại cử tri mỗi lần bật máy.

## 2. Bật backend và giao diện

Mở cửa sổ CMD thứ hai:

```cmd
cd /d D:\HeThongBauCu
venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Giữ cửa sổ này mở. Thử trang trên chính máy này: <http://127.0.0.1:8000/static/register.html>. Nếu không mở được, xem lỗi trong cửa sổ backend trước khi bật tunnel.

## 3. Bật Cloudflare Tunnel

Mở cửa sổ CMD thứ ba. Nếu đã tải `cloudflared-windows-amd64.exe` vào Downloads:

```cmd
"%USERPROFILE%\Downloads\cloudflared-windows-amd64.exe" tunnel --url http://127.0.0.1:8000
```

Tìm dòng `Your quick Tunnel has been created! Visit it at` và lấy link `https://...trycloudflare.com`. Thêm `/static/register.html` vào cuối link để mở trang kích hoạt. Thử link bằng điện thoại đã tắt Wi-Fi để xác nhận truy cập từ ngoài LAN. Không cần chung mạng với máy chạy ứng dụng.

Nếu CMD báo không tìm thấy file, kiểm tra `dir /b "%USERPROFILE%\Downloads\cloudflared*"`. Nếu file không còn, tải bản **Windows 64-bit Executable** từ [Cloudflare](https://developers.cloudflare.com/tunnel/downloads/). Nếu tên hoặc vị trí file khác, dùng đúng đường dẫn tới file `.exe` đã tải.

## Khi dùng và khi dừng

- Giữ máy, PostgreSQL, backend và `cloudflared` chạy trong lúc mọi người thử. Đóng backend có thể làm link trả lỗi `502 Bad gateway`.
- Mỗi lần chạy lại Quick Tunnel có thể nhận **link mới**; đừng dùng link cũ. Ai có link đều có thể truy cập, nên chỉ dùng dữ liệu thử và không gửi mã kích hoạt, mật khẩu hoặc khóa riêng vào nhóm công khai.
- Bản demo cần HTTPS để trình duyệt tạo khóa cử tri; dùng link tunnel cho người thử trên máy khác. HTTP qua IP LAN có thể mở được trang nhưng không kích hoạt được.
- Khi cần dừng, nhấn `Ctrl+C` trong cửa sổ tunnel và backend. Có thể chạy `docker compose stop` ở thư mục dự án để dừng PostgreSQL mà vẫn giữ dữ liệu. **Không dùng `docker compose down -v`**, vì lệnh đó xóa volume dữ liệu.

Hiện `.env` trên máy này đặt `ELECTION_END=2026-10-20T00:00:00Z`: sau thời điểm đó không bỏ phiếu mới được. Nếu muốn thử bỏ phiếu, đặt khoảng thời gian thử phù hợp trong `.env` rồi khởi động lại backend; không thay đổi khóa KMS hoặc xóa DB đang dùng.
