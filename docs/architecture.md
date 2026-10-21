<!--
MỤC ĐÍCH: Mô tả thành phần, đường dữ liệu và ranh giới quyền của bản demo.
PHỤ THUỘC: app/main.py, app/voting/, app/crypto/, db/init.sql và docs/STRUCTURE.md.
LUỒNG: Browser ký → API kiểm tra và ghi phiếu → tally_user đọc, KMS giải mã → trả tổng.
TỰ KIỂM TRA: Đối chiếu route, GRANT và tests/test_attack.py, tests/test_voting.py.
-->

# Kiến trúc bản demo

## Thành phần và luồng

```text
Browser (static/) ──POST /activate, /login, /vote──▶ FastAPI (app/main.py)
       │                                             │
       │ tạo khóa cử tri, ký hai payload              ├─ auth/ ──▶ voters, voter_status
       │                                             └─ voting/ ──▶ used_nonces, votes, voter_status
       │                                                            │
       └──────────── GET /results (admin) ◀── voting/tally.py ◀─────┘
                                         │
                                         └─ crypto/KMS đọc khóa hệ thống
```

`app/main.py` gắn các route theo chức năng và phục vụ bốn trang tại `/static/`.
Browser tạo khóa RSA cử tri; chỉ public key đi qua `/activate`. Private key cử tri ở browser
và có thể xuất thành file sao lưu. `/login` chỉ kiểm tra tài khoản, cấp JWT và `election_id`.
Khi bỏ phiếu, browser ký `ballot` và `cast`; `/vote` xác minh chữ ký, khóa dòng trạng thái,
ghi nonce, phiếu mã hóa và trạng thái trong cùng transaction. Route trả receipt sau commit.

Sau giờ kết thúc, `/results` yêu cầu JWT admin. `tally.py` đọc phiếu bằng `tally_user`,
giải mã trong RAM qua KMS mô phỏng và trả tổng theo ứng viên. API không trả từng phiếu đã giải mã.

## Dữ liệu và quyền

| Bảng | Nội dung chính | Quyền ứng dụng |
| --- | --- | --- |
| `voters` | ID, hash kích hoạt/mật khẩu, public key cử tri | `app_user` đọc, seed và cập nhật cột kích hoạt |
| `candidates` | Ứng viên | Cả ba role đọc |
| `votes` | UUID, ciphertext, wrapped DEK, IV, tag | `app_user` chỉ INSERT; `tally_user` chỉ SELECT |
| `voter_status` | Đã bầu, chữ ký cast, receipt, giờ đã làm tròn | `app_user` đọc/ghi |
| `used_nonces` | Nonce đã dùng | `app_user` chỉ INSERT |

`admin_app` chỉ được đọc `candidates`; tài khoản admin của API nằm trong cấu hình,
không có bảng admin. `tally_user` đọc `votes` và `candidates`, không sửa phiếu.
`votes` không chứa `voter_id`, `candidate_id` hay thời điểm bầu dưới dạng cột riêng.
Nguồn chuẩn của quyền và cột là [db/init.sql](../db/init.sql); các kết nối tương ứng nằm ở
[app/database/database.py](../app/database/database.py).

## Ranh giới tin cậy

Browser và HTTP là đầu vào không tin cậy. Pydantic kiểm tra hình dạng JSON; backend
tự dựng `cast` từ JWT và `ELECTION_ID` rồi xác minh cả hai chữ ký bằng public key đã lưu.
PostgreSQL khóa dòng `voter_status` để hai request đồng thời của một cử tri không cùng thành công.
Quyền DB hạn chế truy vấn nếu một role ứng dụng bị dùng sai.

Đây là bản demo: backend nhìn thấy lựa chọn trước khi mã hóa; KMS và khóa riêng hệ thống
cùng máy với backend. Việc tách bảng chỉ giảm liên kết trực tiếp, không chứng minh ẩn danh.
Các giới hạn khác nằm trong [risk-analysis.md](risk-analysis.md).
