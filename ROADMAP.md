<!--
FILE: ROADMAP.md
MỤC ĐÍCH: Thứ tự tự triển khai từng nhóm file và điều kiện hoàn thành mỗi chặng.
CÁCH DÙNG: Đọc STRUCTURE.md trước, sau đó viết code dưới comment của từng file.
TRẠNG THÁI: Kế hoạch; checkpoint chưa chạy không được đánh dấu hoàn thành.
KHI SỬA: Đồng bộ tên hàm/payload với comment backend, frontend và tài liệu cấu trúc.
-->

# Lộ trình tự code theo luồng dữ liệu

Giữ thiết kế gốc; thay cách đếm 28 file bằng các chặng để file bổ sung không làm sai số bước.
Toàn bộ hợp đồng cụ thể nằm ở [STRUCTURE.md](docs/STRUCTURE.md).

## Chặng 1 — Hiểu và chuẩn bị môi trường

Đọc lần lượt requirements.txt → .env.example → .gitignore → db/01_roles.sh → db/init.sql → docker-compose.yml.
Hiện chỉ chạy PostgreSQL: `docker compose up -d`, dùng image có sẵn, không cần build ứng dụng.

- Hiểu 5 bảng và quyền của 3 role, chưa cần code web.
- Giữ .env thật riêng; thêm ELECTION_ID nếu cần, phải ổn định suốt cuộc bầu cử.
- Rà lại quote password trong 01_roles.sh trước dùng password có ký tự đặc biệt.
- PostgreSQL init chỉ áp dụng cho volume mới; dùng môi trường test riêng cho thử nghiệm phá dữ liệu.

Checkpoint: DB lên tại 127.0.0.1:5432, bảng/role đúng, admin_app không đọc được votes.
Backend/frontend không nằm trong Compose; các chặng sau chạy Python local khi đã viết code.

## Chặng 2 — Cấu hình và kết nối DB

Code app/core/config.py → app/database/database.py → app/database/models.py → app/api/schemas.py.

- Settings quản lý config; database tạo ba session factory.
- Models khớp từng cột trong SQL, không tự tạo bảng bằng app_user.
- Schemas chỉ kiểm tra JSON; không truy vấn DB, không lộ hash/khóa ra response.

Checkpoint: đọc được candidates bằng app_user; INSERT phiếu thử bằng Core inline không cần SELECT/RETURNING.
Chỉ thử trên DB riêng. Phiếu mẫu chưa qua crypto không đưa vào DB bầu cử thật.

## Chặng 3 — Mật mã và giao thức ký

Code app/crypto/kms.py → app/crypto/crypto_service.py → app/crypto/signature_service.py → static/js/crypto.js.

- KMS tạo/nạp cặp RSA hệ thống, giữ thư mục khóa local qua lần restart backend.
- Crypto mã hóa bytes và trả ciphertext/wrapped_dek/iv/tag.
- Signature thống nhất JSON canonical, RSA-PSS salt 32, SHA-256, Base64.
- Browser sinh khóa cử tri; kiểm tra chữ ký browser bằng Python trước khi nối UI.
- Viết test_crypto.py cùng chặng; dùng thư mục khóa tạm và dữ liệu giả.

Checkpoint: round-trip, sửa tag thất bại, cùng plaintext mã hóa khác, restart mở phiếu cũ được; vector JS/Python khớp.

## Chặng 4 — Mật khẩu, JWT và kích hoạt

Code app/auth/auth.py → app/database/seed_voters.py → phần /activate, /login, /candidates trong main.py.

- Password: PBKDF2-HMAC-SHA256 + salt riêng, hash tự mô tả iterations/phiên bản.
- Seed chỉ sinh mã kích hoạt ngẫu nhiên, không sinh khóa RSA cử tri.
- Activate khóa dòng voters, kiểm tra code/public key, lưu hash/password/public key, tạo trạng thái.
- Login chỉ đọc DB và trả JWT + election_id; không sinh lại khóa cử tri.

Checkpoint: seed hai lần không reset tài khoản; activate một lần; password sai/JWT sửa bị từ chối.

## Chặng 5 — Bỏ phiếu trong một transaction

Code app/voting/voting_service.py → route /vote trong main.py → tests/test_voting.py.

```text
JWT hợp lệ → mở transaction → kiểm tra thời gian/voter/candidate/chữ ký
→ khóa voter_status → kiểm tra chưa bầu → INSERT nonce
→ mã hóa envelope → INSERT votes → UPDATE trạng thái → COMMIT → trả receipt
```

- main sở hữu session.begin; service không commit. Tránh begin sau khi session đã autobegin vì truy vấn trước đó.
- Dùng UUID v4, Core inline INSERT, không lấy RETURNING bằng app_user.
- Receipt hash từ sig_cast bytes, không nối sang votes.

Checkpoint: bầu một lần thành công; hai session đồng thời chỉ một thành công; lỗi giữa chừng rollback tất cả.
Phải kiểm thử PostgreSQL thật, không thay bằng SQLite cho kiểm tra khóa dòng.

## Chặng 6 — Kiểm phiếu và admin

Code app/voting/tally.py → /admin/login và /results trong main.py.

- Chỉ cho phép khi now >= ELECTION_END, kiểm tra cả ở service.
- Tally dùng tally_user, mở khóa AES qua KMS rồi đếm.
- Phiếu lỗi làm dừng kết quả, không âm thầm bỏ qua; response chỉ có tổng.

Checkpoint: token cử tri bị chặn; kiểm sớm bị chặn; phiếu hợp lệ cho tổng đúng; phiếu hỏng không tạo tổng sai.

## Chặng 7 — Giao diện

Code register.html → login.html → vote.html → admin.html; dùng chung js/crypto.js.

- Kích hoạt gửi public key, giữ private ở browser và cho backup.
- Login giữ token/election_id, không giữ mật khẩu; token admin riêng.
- Vote ký ballot/cast; chỉ báo thành công sau response commit. Lỗi mạng có thể xảy ra sau commit.
- Admin chỉ hiển thị tổng, không tải khóa/phiếu.

Checkpoint: SV001 kích hoạt → login → bầu B → bầu lại bị chặn → admin xem B tăng 1 sau kết thúc.

## Chặng 8 — Kiểm thử tích hợp và tài liệu

Hoàn thiện test_attack.py và chạy các test đã viết trên môi trường riêng.
Viết docs/architecture.md → technical.md → risk-analysis.md theo comment đầu file.
Cập nhật README theo trạng thái đã kiểm chứng; tài liệu Word có thể sinh lại từ Markdown nguồn.

Checkpoint: có kết quả thực tế cho replay, concurrency, quyền DB, sai chữ ký, sai thời gian, rollback.
Nếu file test chỉ có docstring thì chạy thành công với 0 test không phải chứng minh hệ thống đúng.
