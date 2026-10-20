<!--
FILE: README.md
MỤC ĐÍCH: Cửa vào dự án, nói đúng phần đã có và nơi bắt đầu tự code.
CÁCH CẬP NHẬT: Sau mỗi chặng đã chạy kiểm thử, cập nhật trạng thái tương ứng.
Không ghi tính năng đã hoàn thành khi mới có comment hoặc kế hoạch.
ĐỌC TIẾP: docs/STRUCTURE.md, ROADMAP.md, rồi docstring đầu từng file.
-->

# Hệ thống bầu cử điện tử — khung triển khai

Dự án đang được tự code theo từng chặng. SQL tạo bảng/quyền, Docker và script xuất Word đã có nội dung;
giao diện và các module nghiệp vụ bầu cử vẫn chủ yếu là khung, chưa phải ứng dụng chạy hoàn chỉnh.
Chặng 1 đã kiểm tra thực tế: PostgreSQL healthy tại 127.0.0.1:5433; 5 kiểm tra khởi tạo/quyền DB đạt.
Chặng 2 đã hoàn thành: cấu hình, ba kết nối/session DB, ánh xạ 5 bảng và schema API đã có code;
checkpoint SQLAlchemy async trên PostgreSQL thật đạt, gồm đọc candidates và INSERT Core inline luôn rollback.
Chặng 3 đã hoàn thành checkpoint: KMS đã tạo/nạp lại cặp RSA và bọc/mở khóa AES bằng RSA-OAEP;
AES-GCM đã mã hóa/giải mã phiếu; Python đã chuẩn hóa payload và kiểm tra chữ ký RSA-PSS.
WebCrypto đã tạo khóa và ký trong browser; chữ ký browser được Python xác minh bằng dữ liệu giả.
16 kiểm tra mật mã đạt; giao diện chưa nối helper, các chặng 4–8 chưa triển khai.

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

Giữ các thư mục app, static, db, tests, docs. Bên trong app gom thành core/, auth/, api/, database/, crypto/, voting/; main.py là điểm vào. Bổ sung app/voting/voting_service.py, static/js/crypto.js và test_voting.py để tách nhiệm vụ rõ.
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

Backend sau này dùng app_user/admin_app/tally_user theo nhiệm vụ, không dùng postgres.
Volume pgdata giữ nguyên dữ liệu; lần khởi tạo DB mới tạo bảng, role và 3 ứng viên.
Chưa có cử tri mẫu vì seed script hiện chưa được triển khai.

## Sau khi viết backend, chạy trên máy local

Kiểm tra .env theo mẫu: ba DB URL dùng driver `postgresql+asyncpg` và 127.0.0.1;
KMS_KEY_DIR dùng ./kms_keys. Không dùng hostname postgres của mạng Docker cho backend local.
Không ghi đè .env đang dùng bằng file mẫu.

```powershell
# Chạy từ thư mục gốc, trong môi trường Python đã cài requirements
python -m app.database.seed_voters
uvicorn app.main:app --reload

# Kiểm tra KMS, AES-GCM và vector chữ ký WebCrypto/Python; password/JWT chưa có test
python -m unittest tests.test_crypto

# Script xuất Word đã có thể chạy độc lập
python docs/build_flow_docx.py
```

Sao chép .env.example thành .env nếu chưa có, thay secret/mật khẩu mẫu. Không ghi đè .env đang dùng.
SQL init chỉ chạy tự động khi volume DB mới; không xóa volume có dữ liệu để thử lại.
Dependency đang giữ phiên bản cũ của project, cần đánh giá và kiểm thử trước triển khai thật.
