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
- 01_roles.sh dùng psql \getenv, quote literal và format %L để nhận password có ký tự đặc biệt.
- PostgreSQL init chỉ áp dụng cho volume mới; dùng môi trường test riêng cho thử nghiệm phá dữ liệu.

Checkpoint: DB lên tại 127.0.0.1:5433, bảng/role đúng, admin_app không đọc được votes.
Backend/frontend không nằm trong Compose; các chặng sau chạy Python local khi đã viết code.

**Đã hoàn thành checkpoint chặng 1:** PostgreSQL healthy trên cổng 5433; đủ 5 bảng,
3 ứng viên mẫu và 3 role không có quyền superuser/tạo DB/tạo role.
Ba role đăng nhập được; app_user/admin_app không SELECT votes; tally_user đọc được và không sửa phiếu.
5 kiểm tra trong `tests/test_database_setup.py` đã chạy đạt, gồm quote password có dấu nháy/backslash.
Chạy lại bằng `python -m unittest tests.test_database_setup -v` khi Docker đang chạy.
Chặng 2 và 3 đã hoàn thành checkpoint; chặng 4 đang triển khai; các chặng 5–8 chưa triển khai.

## Chặng 2 — Cấu hình và kết nối DB

Code app/core/config.py → app/database/database.py → app/database/models.py → app/api/schemas.py.

- Settings quản lý config; database tạo ba `AsyncSession` factory dùng asyncpg.
- Models khớp từng cột trong SQL, không tự tạo bảng bằng app_user.
- Schemas chỉ kiểm tra JSON; không truy vấn DB, không lộ hash/khóa ra response.

Checkpoint: đọc được candidates bằng app_user; INSERT phiếu thử bằng Core inline không cần SELECT/RETURNING.
Chỉ thử trên DB riêng. Phiếu mẫu chưa qua crypto không đưa vào DB bầu cử thật.

**Đã hoàn thành checkpoint chặng 2 ngày 2026-10-17:**

- `config.py` dùng thống nhất `APP_DATABASE_URL`, `ADMIN_DATABASE_URL`, `TALLY_DATABASE_URL`.
- `database.py` đã có `Base`, ba AsyncEngine, ba AsyncSession factory và `get_db()`; 3 kiểm tra trong
  `tests/test_async_database.py` chạy đạt bằng Python trong `venv`.
- `models.py` đã ánh xạ đủ 5 bảng; kiểm tra metadata trả về `candidates`, `used_nonces`,
  `voter_status`, `voters`, `votes`.
- `schemas.py` đã triển khai đủ request/response của thiết kế; 17 kiểm tra schema chạy đạt.
- Hai kiểm tra trong `tests/test_stage2_postgres.py` xác nhận `app_user` đọc candidates qua SQLAlchemy async,
  INSERT phiếu giả bằng Core `insert(Vote).inline()` không cần SELECT/RETURNING, rồi luôn ROLLBACK;
  `tally_user` xác nhận phiếu giả không tồn tại sau test.
- Toàn bộ 27 kiểm tra hiện có chạy đạt bằng `python -m unittest discover -v` khi Docker healthy.

## Chặng 3 — Mật mã và giao thức ký

Code app/crypto/kms.py → app/crypto/crypto_service.py → app/crypto/signature_service.py → static/js/crypto.js.

- KMS tạo/nạp cặp RSA hệ thống, giữ thư mục khóa local qua lần restart backend.
- Crypto mã hóa bytes và trả ciphertext/wrapped_dek/iv/tag.
- Signature thống nhất JSON canonical, RSA-PSS salt 32, SHA-256, Base64.
- Browser sinh khóa cử tri; kiểm tra chữ ký browser bằng Python trước khi nối UI.
- Viết test_crypto.py cùng chặng; dùng thư mục khóa tạm và dữ liệu giả.

**Đã hoàn thành checkpoint chặng 3 ngày 2026-10-20:**

- `kms.py` đã tạo hoặc nạp lại RSA 2048, lưu private key PKCS8 và public key SPKI dạng PEM,
  bọc/mở DEK 32 byte bằng RSA-OAEP SHA-256 và không tự thay private key bị mất.
- 6 kiểm tra KMS trong `tests/test_crypto.py` chạy đạt bằng thư mục tạm: round-trip, dùng lại khóa sau
  khởi động, phục hồi public key, chặn mất private key, chặn DEK sai độ dài và từ chối private key khác.
- `crypto_service.py` đã mã hóa phiếu bằng AES-256-GCM với DEK và IV mới cho mỗi phiếu,
  tách ciphertext/tag, bọc DEK qua KMS và giải mã có kiểm tra tính toàn vẹn.
  4 kiểm tra AES-GCM trong `tests/test_crypto.py` đạt bằng khóa tạm: round-trip,
  DEK/IV mới, từ chối dữ liệu bị sửa và độ dài không hợp lệ.
- `signature_service.py` đã chuẩn hóa ballot/cast thành JSON UTF-8, nạp public key cử tri
  SPKI PEM RSA 2048, giải mã Base64 chuẩn và kiểm tra RSA-PSS SHA-256/salt 32 byte.
  5 kiểm tra Python trong `tests/test_crypto.py` đạt bằng khóa cử tri tạm trong RAM.
- `static/js/crypto.js` đã có WebCrypto RSA-PSS, SPKI/PKCS8, JSON canonical, chữ ký Base64,
  nonce và helper lưu/nạp khóa demo trong browser; chưa nối vào giao diện.
- Vector chữ ký `ballot` và `cast` tạo trong browser thật được Python xác minh; sửa ứng viên
  hoặc voter_id bị từ chối. Test cố định chỉ lưu public key và chữ ký giả trong `tests/test_crypto.py`.
  16 kiểm tra mật mã đạt; xuất/nhập khóa và localStorage cũng đã kiểm tra trong browser.

Checkpoint: round-trip, sửa tag thất bại, cùng plaintext mã hóa khác, restart mở phiếu cũ được; vector JS/Python khớp.

## Chặng 4 — Mật khẩu, JWT và kích hoạt

Code app/auth/auth.py → app/database/seed_voters.py → phần /activate, /login, /candidates trong main.py.

- Password: PBKDF2-HMAC-SHA256 + salt riêng, hash tự mô tả iterations/phiên bản.
- Seed chỉ sinh mã kích hoạt ngẫu nhiên, không sinh khóa RSA cử tri.
- Activate khóa dòng voters, kiểm tra code/public key, lưu hash/password/public key, tạo trạng thái.
- Login chỉ đọc DB và trả JWT + election_id; không sinh lại khóa cử tri.

Checkpoint: seed hai lần không reset tài khoản; activate một lần; password sai/JWT sửa bị từ chối.

**Đang triển khai chặng 4; cập nhật ngày 2026-10-21:** `auth.py` đã có hash/verify mật khẩu
PBKDF2-HMAC-SHA256 với salt riêng và hash lưu số vòng lặp; mã kích hoạt ngẫu nhiên được
băm SHA-256 và so sánh bằng `hmac.compare_digest`. Hàm tạo/xác minh JWT dùng HS256,
kiểm tra chữ ký, thời hạn, subject và role. Bearer dependency lấy subject của đúng role voter/admin,
trả 401 cho token thiếu/sai và 403 cho token sai quyền. Hàm đối chiếu admin đọc cấu hình,
so sánh username/password bằng `hmac.compare_digest` và không đọc bảng voters.
15 kiểm tra mật khẩu/cấu hình/mã kích hoạt/JWT/Bearer/admin trong `tests/test_crypto.py` đạt;
`seed_voters.py` đã có code nạp 10 cử tri mẫu: chỉ lưu hash mã kích hoạt, bỏ qua voter_id đã có,
chỉ hiện mã sau commit. Hai test với session giả kiểm tra chạy lại và lỗi trước commit đạt;
53 kiểm tra không cần PostgreSQL đạt. Seed chưa được kiểm trên PostgreSQL thật;
route kích hoạt/đăng nhập vẫn là khung, checkpoint chặng 4 chưa hoàn thành.

## Chặng 5 — Bỏ phiếu trong một transaction

Code app/voting/voting_service.py → route /vote trong main.py → tests/test_voting.py.

```text
JWT hợp lệ → mở transaction → kiểm tra thời gian/voter/candidate/chữ ký
→ khóa voter_status → kiểm tra chưa bầu → INSERT nonce
→ mã hóa envelope → INSERT votes → UPDATE trạng thái → COMMIT → trả receipt
```

- main sở hữu `async with session.begin()`; service không commit. Tránh begin sau khi session đã autobegin vì truy vấn trước đó.
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
