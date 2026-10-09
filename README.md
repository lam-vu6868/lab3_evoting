<!--
FILE:        README.md
BƯỚC:        28/28
MỤC ĐÍCH:    Hướng dẫn cài đặt, chạy demo, cấu trúc project, tác giả
PHỤ THUỘC:   Toàn bộ project
BƯỚC TIẾP:   HOÀN TẤT — Nộp bài
-->

# 2 FILE: `README.md` và `ROADMAP.md`

Bạn copy 2 file dưới vào đúng vị trí trong project. Mình viết theo đúng format header đã thống nhất.

---

## 📄 FILE 1: `README.md`

Đặt tại: `lab3_evoting/README.md`

```markdown
<!--
FILE:        README.md
BƯỚC:        28/28
MỤC ĐÍCH:    Hướng dẫn cài đặt, chạy demo, cấu trúc project, tác giả
PHỤ THUỘC:   Toàn bộ project
BƯỚC TIẾP:   HOÀN TẤT — Nộp bài
-->

# 🔐 Lab 3 — Secure E-Voting Database System

> Hệ thống bầu cử điện tử bảo mật cho Hội đồng Sinh viên — Bài Lab môn An toàn thông tin.

---

## 📌 Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Tính năng bảo mật](#2-tính-năng-bảo-mật)
3. [Kiến trúc hệ thống](#3-kiến-trúc-hệ-thống)
4. [Công nghệ sử dụng](#4-công-nghệ-sử-dụng)
5. [Cài đặt & Chạy](#5-cài-đặt--chạy)
6. [Cấu trúc thư mục](#6-cấu-trúc-thư-mục)
7. [Hướng dẫn demo](#7-hướng-dẫn-demo)
8. [Kịch bản tấn công đã chống](#8-kịch-bản-tấn-công-đã-chống)
9. [Tài liệu tham khảo](#9-tài-liệu-tham-khảo)
10. [Tác giả](#10-tác-giả)

---

## 1. Giới thiệu

Đây là hệ thống bầu cử điện tử cho Hội đồng Sinh viên, được thiết kế để đáp ứng **4 tính chất bảo mật bắt buộc**:

| Tính chất                           | Ý nghĩa                             | Cách đáp ứng                        |
| ----------------------------------- | ----------------------------------- | ----------------------------------- |
| **Confidentiality** (Bảo mật)       | Không ai đọc được lá phiếu trong DB | AES-256-GCM mã hóa trước khi INSERT |
| **Anonymity** (Ẩn danh)             | Không biết cử tri bầu cho ai        | Bảng `votes` KHÔNG có `voter_id`    |
| **Non-repudiation** (Chống chối bỏ) | Cử tri không thể nói "tôi chưa bầu" | Chữ ký số RSA của cử tri            |
| **Verifiability** (Kiểm chứng)      | Admin thấy tổng, không thấy từng lá | Tally Service chỉ trả aggregate     |

**Nguyên tắc cốt lõi:** Admin **không giữ key**, **không có quyền** đọc ciphertext, **không có endpoint** xem từng lá phiếu. Chỉ có Tally Service (chạy trong process backend, không expose HTTP) mới gọi được KMS để giải mã.

---

## 2. Tính năng bảo mật

### 2.1. Mã hóa

- **Hybrid Encryption**: AES-256-GCM (mã hóa dữ liệu) + RSA-2048-OAEP (wrap chìa AES).
- **IV (nonce) ngẫu nhiên** cho mỗi lá phiếu — chống pattern analysis.
- **Auth Tag** của GCM — phát hiện mọi sửa đổi ciphertext.

### 2.2. Key Management

- Private key RSA **không nằm trong source code**.
- Giả lập KMS bằng class `KMS` — private key chỉ tồn tại trong RAM.
- File `kms_private.pem` có quyền `chmod 600` (chỉ owner đọc).
- **Không có API nào** trả private key ra ngoài.

### 2.3. Chống tấn công

| Tấn công             | Cơ chế chống                                |
| -------------------- | ------------------------------------------- |
| **SQL Injection**    | SQLAlchemy ORM (parameterized queries)      |
| **Replay Attack**    | Nonce unique + timestamp ≤ 5 phút           |
| **Double Voting**    | UNIQUE constraint + `SELECT ... FOR UPDATE` |
| **Race Condition**   | Transaction + row-level lock                |
| **Giả mạo chữ ký**   | RSA signature verify với public key cử tri  |
| **Đọc DB trực tiếp** | GRANT hạn chế theo role                     |
| **Đọc source code**  | `.env` + `.gitignore`                       |

### 2.4. Phân quyền theo nguyên tắc Least Privilege

- **`app_user`**: INSERT votes, UPDATE voter_status, INSERT nonces. Không DELETE.
- **`admin_app`**: CHỈ SELECT candidates. Không đọc được `votes`.
- **`tally_user`**: CHỈ SELECT votes + candidates.

---

## 3. Kiến trúc hệ thống
```

┌──────────────┐ ┌─────────────────────────┐ ┌─────────────────┐
│ Cử tri │──HTTPS─▶│ FastAPI Server │──SQL──▶│ PostgreSQL │
│ (Browser) │ │ ┌───────────────────┐ │ │ │
└──────────────┘ │ │ Auth (JWT) │ │ │ voters │
│ │ Signature Verify │ │ │ candidates │
┌──────────────┐ │ │ Crypto Service │ │ │ votes │
│ Admin │──HTTPS─▶│ │ Tally Service │ │ │ voter_status │
│ (Browser) │ │ └─────────┬─────────┘ │ │ used_nonces │
└──────────────┘ │ │ │ └─────────────────┘
└────────────┼────────────┘
│ gọi wrap/unwrap
▼
┌───────────────┐
│ KMS (class) │
│ RSA keypair │
│ (RAM only) │
└───────────────┘

````

**Chi tiết luồng xử lý:** Xem [`ROADMAP.md`](./ROADMAP.md) mục 4.

---

## 4. Công nghệ sử dụng

| Thành phần | Công nghệ | Phiên bản |
|---|---|---|
| Ngôn ngữ | Python | 3.11+ |
| Framework | FastAPI | 0.110.0 |
| ORM | SQLAlchemy | 2.0.29 |
| Database | PostgreSQL | 16 |
| Crypto | `cryptography` | 42.0.5 |
| JWT | `python-jose` | 3.3.0 |
| Container | Docker + Docker Compose | Latest |
| Frontend | HTML + JS thuần + Bootstrap CDN | — |

---

## 5. Cài đặt & Chạy

### 5.1. Yêu cầu hệ thống
- Docker Desktop (hoặc Docker Engine + Docker Compose).
- Python 3.11+ (chỉ cần nếu muốn chạy app ngoài Docker).
- 4 GB RAM trống.

### 5.2. Cài đặt

```bash
# 1. Clone project (hoặc giải nén file zip)
cd lab3_evoting

# 2. Copy file mẫu .env
cp .env.example .env

# 3. Sinh JWT secret ngẫu nhiên
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"
# Copy output vào .env (thay dòng JWT_SECRET=...)

# 4. Sửa .env: đổi tất cả "change_me" thành password thật
# Không cần phức tạp, ví dụ:
#   POSTGRES_ROOT_PASSWORD=root123
#   APP_USER_PASSWORD=app123
#   ADMIN_USER_PASSWORD=admin123
#   TALLY_USER_PASSWORD=tally123
#   ADMIN_USERNAME=admin
#   ADMIN_PASSWORD=admin123
````

### 5.3. Chạy hệ thống

```bash
# Khởi động PostgreSQL + App
docker-compose up -d

# Xem log (theo dõi app đang chạy)
docker-compose logs -f app

# Kiểm tra containers đã chạy chưa
docker-compose ps
```

Khi thấy log:

```
evoting_app  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

→ Truy cập http://localhost:8000

### 5.4. Seed dữ liệu mẫu

```bash
# Tạo 10 cử tri mẫu + sinh RSA keypair cho mỗi người
docker-compose exec app python -m app.seed_voters
```

### 5.5. Dừng hệ thống

```bash
# Dừng nhưng giữ data
docker-compose down

# Dừng và xóa sạch data (reset về ban đầu)
docker-compose down -v && rm -rf pgdata kms_keys
```

---

## 6. Cấu trúc thư mục

```
lab3_evoting/
├── app/                          # Backend FastAPI
│   ├── __init__.py
│   ├── config.py                 # Load .env
│   ├── kms.py                    # Giả lập KMS
│   ├── crypto_service.py         # AES-256-GCM
│   ├── signature_service.py      # Chữ ký số cử tri
│   ├── database.py               # Kết nối PostgreSQL
│   ├── models.py                 # ORM tables
│   ├── schemas.py                # Pydantic
│   ├── auth.py                   # JWT + password
│   ├── tally.py                  # Tally Service
│   ├── seed_voters.py            # Seed cử tri mẫu
│   └── main.py                   # FastAPI routes
├── static/                       # Frontend
│   ├── register.html
│   ├── login.html
│   ├── vote.html
│   └── admin.html
├── db/init.sql                   # Tạo bảng + user + GRANT
├── docs/                         # Tài liệu
│   ├── architecture.md
│   ├── technical.md
│   └── risk-analysis.md
├── tests/                        # Test
│   ├── test_crypto.py
│   └── test_attack.py
├── kms_keys/                     # 🔒 RSA key (KHÔNG commit)
├── pgdata/                       # 🔒 PostgreSQL data (KHÔNG commit)
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md                     # ← file này
└── ROADMAP.md                    # Lộ trình làm + luồng xử lý
```

---

## 7. Hướng dẫn demo

### 7.1. Truy cập các trang

| Trang       | URL                                        | Mục đích           |
| ----------- | ------------------------------------------ | ------------------ |
| Swagger API | http://localhost:8000/docs                 | Test API trực tiếp |
| Đăng ký     | http://localhost:8000/static/register.html | Tạo cử tri mới     |
| Đăng nhập   | http://localhost:8000/static/login.html    | Cử tri login       |
| Bỏ phiếu    | http://localhost:8000/static/vote.html     | Chọn đại biểu      |
| Admin       | http://localhost:8000/static/admin.html    | Xem kết quả        |

### 7.2. Demo 3 kịch bản chính

**Kịch bản 1: Bỏ phiếu thành công**

1. Đăng ký cử tri `SV001` → nhận private key (lưu localStorage).
2. Đăng nhập → nhận JWT.
3. Chọn đại biểu "Nguyễn Văn A" → bấm "Bỏ phiếu".
4. Nhận receipt hash.

**Kịch bản 2: Bỏ phiếu lần 2 (bị chặn)**

1. Đăng nhập lại `SV001`.
2. Chọn đại biểu khác → bấm "Bỏ phiếu".
3. Nhận lỗi: **"Bạn đã bỏ phiếu rồi"**.

**Kịch bản 3: Admin xem kết quả**

1. Vào `/static/admin.html`.
2. Nhập username/password admin (từ `.env`).
3. Xem bảng: A: X phiếu, B: Y phiếu, C: Z phiếu.

### 7.3. Demo tấn công (cho buổi bảo vệ)

```bash
# Chạy script tấn công tự động
docker-compose exec app python -m tests.test_attack
```

Script sẽ thử:

- SQL Injection vào form login.
- Replay request vote.
- Double vote với 2 request đồng thời.
- Kết nối DB bằng `admin_app` rồi SELECT votes → kỳ vọng bị từ chối.
- Sửa payload rồi gửi → chữ ký sai → bị từ chối.

---

## 8. Kịch bản tấn công đã chống

| #   | Tấn công          | Cách chống                        | File liên quan             |
| --- | ----------------- | --------------------------------- | -------------------------- |
| 1   | SQL Injection     | SQLAlchemy ORM                    | `app/main.py`              |
| 2   | Replay Attack     | Nonce + Timestamp                 | `app/main.py`, `models.py` |
| 3   | Double Voting     | UNIQUE + FOR UPDATE               | `app/main.py`              |
| 4   | Race Condition    | Transaction + row lock            | `app/main.py`              |
| 5   | Đọc DB trực tiếp  | GRANT theo role                   | `db/init.sql`              |
| 6   | Đọc source code   | `.env` + `.gitignore`             | `.gitignore`               |
| 7   | Giả mạo chữ ký    | RSA verify                        | `signature_service.py`     |
| 8   | Đọc private key   | chmod 600 + RAM only              | `kms.py`                   |
| 9   | Timing attack     | Batch tally                       | `tally.py`                 |
| 10  | Brute-force login | (chưa có — ghi vào risk analysis) | —                          |

---

## 9. Tài liệu tham khảo

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [cryptography.io — AES-GCM](https://cryptography.io/en/latest/hazmat/primitives/aead/)
- [PostgreSQL GRANT](https://www.postgresql.org/docs/current/sql-grant.html)
- [NIST SP 800-38D — GCM Mode](https://csrc.nist.gov/publications/detail/sp/800-38d/final)
- [OWASP — SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

## 10. Tác giả

| Vai trò                        | Họ tên  | MSSV     | Email     |
| ------------------------------ | ------- | -------- | --------- |
| Nhóm trưởng (Backend + Crypto) | [Tên A] | [MSSV A] | [email A] |
| Thành viên (DB + UI + Docs)    | [Tên B] | [MSSV B] | [email B] |

**Lớp:** 26TH02
**Giảng viên hướng dẫn:** Dương Quang Sinh
**Ngày nộp:** [DD/MM/YYYY]

---
