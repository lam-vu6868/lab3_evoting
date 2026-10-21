<!--
FILE: README.md
MỤC ĐÍCH: Cửa vào dự án, nói đúng phần đã có và nơi bắt đầu tự code.
CÁCH CẬP NHẬT: Sau mỗi chặng đã chạy kiểm thử, cập nhật trạng thái tương ứng.
Không ghi tính năng đã hoàn thành khi mới có comment hoặc kế hoạch.
ĐỌC TIẾP: docs/STRUCTURE.md, ROADMAP.md, rồi docstring đầu từng file.
-->

# Hệ thống bầu cử điện tử — khung triển khai

Dự án đang được tự code theo từng chặng. SQL tạo bảng/quyền, Docker và script xuất Word đã có nội dung;
giao diện vẫn là khung, chưa phải ứng dụng chạy hoàn chỉnh.
Chặng 1 đã kiểm tra thực tế: PostgreSQL healthy tại 127.0.0.1:5433; 5 kiểm tra khởi tạo/quyền DB đạt.
Chặng 2 đã hoàn thành: cấu hình, ba kết nối/session DB, ánh xạ 5 bảng và schema API đã có code;
checkpoint SQLAlchemy async trên PostgreSQL thật đạt, gồm đọc candidates và INSERT Core inline luôn rollback.
Chặng 3 đã hoàn thành checkpoint: KMS đã tạo/nạp lại cặp RSA và bọc/mở khóa AES bằng RSA-OAEP;
AES-GCM đã mã hóa/giải mã phiếu; Python đã chuẩn hóa payload và kiểm tra chữ ký RSA-PSS.
WebCrypto đã tạo khóa và ký trong browser; chữ ký browser được Python xác minh bằng dữ liệu giả.
Chặng 4 đã hoàn thành checkpoint: seed, POST /activate, POST /login và GET /candidates đã có code.
63 kiểm tra không cần PostgreSQL đạt; 3 kiểm tra trên database thử nghiệm riêng xác nhận seed chạy lại,
kích hoạt đồng thời chỉ một lần thành công, đăng nhập và đọc ứng viên bằng app_user. 5 kiểm tra
cấu trúc/quyền DB hiện có cũng đạt.
Chặng 5 đã hoàn thành checkpoint: POST /vote kiểm tra thời gian, hai chữ ký, cử tri và ứng viên;
khóa dòng trạng thái, ghi nonce/phiếu/trạng thái trong một transaction rồi mới trả biên nhận.
7 kiểm tra trên PostgreSQL riêng đạt, gồm bầu đồng thời, nonce trùng và rollback khi lỗi.
Chặng 6 đã hoàn thành checkpoint: POST /admin/login cấp JWT admin; GET /results chỉ đọc bằng tally_user
sau giờ kết thúc, giải mã phiếu trong RAM và chỉ trả tổng. 5 kiểm tra đạt, gồm đếm phiếu giả đã mã hóa,
chặn kiểm sớm/JWT cử tri, phiếu lỗi và truy vấn bảng rỗng trên PostgreSQL riêng.
Giao diện chưa nối helper; các chặng 7–8 chưa triển khai.

## Bắt đầu tại đây

1. Đọc [bản đồ thư mục và hợp đồng dữ liệu](docs/STRUCTURE.md).
2. Làm từng chặng trong [ROADMAP.md](ROADMAP.md).
3. Mở comment đầu file đang làm: mục đích, phụ thuộc, thứ tự viết code và tự kiểm tra.
4. Dùng [luồng dữ liệu 10 phần](docs/Luong_du_lieu_he_thong_bau_cu.md) hoặc [bản Word](docs/Luong_du_lieu_he_thong_bau_cu.docx) để theo ví dụ SV001.

## Thiết kế giữ nguyên

- PostgreSQL: voters, candidates, votes, voter_status, used_nonces.
- Role: app_user nhận phiếu, admin_app chỉ đọc ứng viên, tally_user đọc để kiểm phiếu.
- Cử tri có sẵn → kích hoạt bằng mã → browser tạo khóa RSA → đăng nhập nhận JWT → ký hai nội dung và gửi phiếu.
- Backend mã hóa phiếu bằng AES-256-GCM, dùng RSA-OAEP của KMS bảo vệ khóa AES.
- Một transaction ghi nonce, phiếu và trạng thái; khóa dòng để chống bỏ phiếu đồng thời.
- Tally giải mã sau thời điểm kết thúc và chỉ trả tổng qua API.

Backend thấy lựa chọn khi nhận phiếu. KMS là mô phỏng trong backend; tách bảng không bảo đảm ẩn danh tuyệt đối.
Các giới hạn cần phân tích nằm trong hướng dẫn đầu [docs/risk-analysis.md](docs/risk-analysis.md).

## Thay đổi về cấu trúc

Giữ các thư mục app, static, db, tests, docs. Bên trong app gom thành core/, auth/, api/, database/, crypto/, voting/; main.py là điểm vào và gắn route. POST /activate, /login và /admin/login nằm trong app/auth/; GET /candidates nằm trong app/api/; POST /vote và GET /results nằm trong app/voting/.
register.html vẫn giữ tên nhưng thực hiện kích hoạt qua /activate, không đăng ký cử tri tự do.
.gitignore bảo vệ cấu hình riêng; docs/tests được quản lý trong Git.

## Hiện tại: chỉ chạy database trong Docker

Compose chỉ có service postgres, dùng image PostgreSQL có sẵn; không build image frontend/backend.
Chỉ cần docker-compose.yml và các script trong db/ để khởi tạo database.

```powershell
# Chạy PostgreSQL
docker compose up -d
docker compose ps
docker compose logs postgres

# Kiểm tra chặng 1: bảng, role, đăng nhập và phân quyền
python -m unittest tests.test_database_setup -v

# Kiểm tra checkpoint PostgreSQL của chặng 2; phiếu giả luôn rollback
python -m unittest tests.test_stage2_postgres -v

# Mở psql trong container để xem bảng
docker compose exec postgres psql -U postgres -d evoting -c "\dt"

# Dừng container, giữ dữ liệu
docker compose stop
```

Kết nối từ DBeaver/pgAdmin hoặc backend chạy trên máy:

| Trường | Giá trị |
| --- | --- |
| Host | 127.0.0.1 |
| Port | 5433 |
| Database | evoting |
| User để học/quản trị DB | postgres |
| Password | Giá trị POSTGRES_ROOT_PASSWORD trong .env |

Code bỏ phiếu dùng app_user; kiểm phiếu dùng tally_user. admin_app chỉ có quyền đọc ứng viên và không đọc phiếu; không dùng postgres cho nghiệp vụ.
Volume pgdata giữ nguyên dữ liệu; lần khởi tạo DB mới tạo bảng, role và 3 ứng viên.
Seed đã được kiểm trên database thử nghiệm riêng; chưa xác nhận đã chạy trên database `evoting`.

## Sau khi viết backend, chạy trên máy local

Kiểm tra .env theo mẫu: ba DB URL dùng driver `postgresql+asyncpg` và 127.0.0.1;
KMS_KEY_DIR dùng ./kms_keys. Không dùng hostname postgres của mạng Docker cho backend local.
Không ghi đè .env đang dùng bằng file mẫu.

```powershell
# Chạy từ thư mục gốc, trong môi trường Python đã cài requirements
python -m app.database.seed_voters
uvicorn app.main:app --reload

# Kiểm tra KMS, AES-GCM, chữ ký WebCrypto/Python, mật khẩu, mã kích hoạt và JWT
python -m unittest tests.test_crypto

# Kiểm tra route kích hoạt với session giả, không ghi PostgreSQL
python -m unittest tests.test_activate -v

# Kiểm tra route đăng nhập với session giả, không ghi PostgreSQL
python -m unittest tests.test_login -v

# Kiểm tra ứng viên với session giả
python -m unittest tests.test_candidates -v

# Chỉ chạy khi đã chuẩn bị database thử nghiệm riêng, không dùng evoting đang dùng
$env:STAGE4_TEST_DB_NAME="evoting_stage4_test_20261021"
python -m unittest tests.test_stage4_postgres -v
Remove-Item Env:STAGE4_TEST_DB_NAME

# Chỉ chạy trên DB thử nghiệm đã nạp init.sql; test ghi cử tri/phiếu giả và giữ dữ liệu
$env:STAGE5_TEST_DB_NAME="evoting_stage5_test_20261021"
python -m unittest tests.test_voting -v
Remove-Item Env:STAGE5_TEST_DB_NAME

# Chỉ chạy trên DB thử nghiệm chặng 6 đã nạp init.sql; test đọc bằng tally_user
$env:STAGE6_TEST_DB_NAME="evoting_stage6_test_20261021"
python -m unittest tests.test_tally -v
Remove-Item Env:STAGE6_TEST_DB_NAME

# Script xuất Word đã có thể chạy độc lập
python docs/build_flow_docx.py
```

Sao chép .env.example thành .env nếu chưa có, thay secret/mật khẩu mẫu. Không ghi đè .env đang dùng.
SQL init chỉ chạy tự động khi volume DB mới; không xóa volume có dữ liệu để thử lại.
Dependency đang giữ phiên bản cũ của project, cần đánh giá và kiểm thử trước triển khai thật.
