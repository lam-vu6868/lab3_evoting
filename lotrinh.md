
> **Lưu ý:** Đây là project học thuật cho môn An toàn thông tin. Không sử dụng cho bầu cử thực tế mà không qua kiểm định bảo mật chuyên nghiệp.
```

---

## 📄 FILE 2: `ROADMAP.md`

Đặt tại: `lab3_evoting/ROADMAP.md`

```markdown
<!--
FILE:        ROADMAP.md
BƯỚC:        (tài liệu bổ trợ — không tính vào 28 bước code)
MỤC ĐÍCH:    Lộ trình thực hiện từng chặng + luồng xử lý chi tiết
PHỤ THUỘC:   README.md
BƯỚC TIẾP:   Bắt đầu code theo Bước 01
-->

# 🗺️ ROADMAP — Lộ trình làm Lab 3

> File này mô tả **từng chặng làm** và **luồng xử lý chi tiết** của hệ thống.
> Đọc từ trên xuống dưới. Không bỏ qua bước nào.

---

## 📌 Mục lục

1. [Tổng quan lộ trình](#1-tổng-quan-lộ-trình)
2. [Sơ đồ phụ thuộc giữa các file](#2-sơ-đồ-phụ-thuộc-giữa-các-file)
3. [Chi tiết 8 chặng](#3-chi-tiết-8-chặng)
4. [Luồng xử lý chi tiết](#4-luồng-xử-lý-chi-tiết)
5. [Checklist theo ngày](#5-checklist-theo-ngày)

---

## 1. Tổng quan lộ trình

Chia làm **8 chặng**, tổng cộng **28 bước** (tương ứng 28 file).

```
CHẶNG 1: SETUP              (Bước 01-06)  — 6 file  — Ngày 1-2
CHẶNG 2: CRYPTO LAYER       (Bước 07-11)  — 5 file  — Ngày 3-4
CHẶNG 3: DATABASE LAYER     (Bước 12-14)  — 3 file  — Ngày 5
CHẶNG 4: AUTH + TALLY       (Bước 15-16)  — 2 file  — Ngày 6-7
CHẶNG 5: API + SEED         (Bước 17-18)  — 2 file  — Ngày 8-9
CHẶNG 6: FRONTEND           (Bước 19-22)  — 4 file  — Ngày 10
CHẶNG 7: TEST               (Bước 23-24)  — 2 file  — Ngày 11-12
CHẶNG 8: DOCS + NỘP         (Bước 25-28)  — 4 file  — Ngày 13-14
```

**Nguyên tắc vàng:**
- **Không nhảy bước.** File sau phụ thuộc file trước.
- **Test từng chặng** trước khi sang chặng tiếp.
- **Commit Git** sau mỗi chặng hoàn thành.

---

## 2. Sơ đồ phụ thuộc giữa các file

```
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 1: SETUP                                           │
│                                                          │
│  requirements.txt ──┐                                    │
│  .env.example       │                                    │
│  .gitignore         │                                    │
│  Dockerfile ────────┼──▶ docker-compose.yml              │
│  db/init.sql ───────┘                                    │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 2: CRYPTO LAYER                                    │
│                                                          │
│  __init__.py                                             │
│  config.py ──┬──▶ kms.py ──▶ crypto_service.py           │
│              └──▶ signature_service.py                   │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 3: DATABASE LAYER                                  │
│                                                          │
│  database.py ──▶ models.py ──▶ schemas.py                │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 4: AUTH + TALLY                                    │
│                                                          │
│  auth.py                                                 │
│  tally.py (cần models + crypto)                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 5: API + SEED                                      │
│                                                          │
│  seed_voters.py                                          │
│  main.py (gom tất cả lại)                                │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 6: FRONTEND                                        │
│                                                          │
│  register.html / login.html / vote.html / admin.html     │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 7: TEST                                            │
│                                                          │
│  test_crypto.py / test_attack.py                         │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CHẶNG 8: DOCS + NỘP                                      │
│                                                          │
│  architecture.md / technical.md / risk-analysis.md       │
│  README.md                                               │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Chi tiết 8 chặng

### 🟢 CHẶNG 1: SETUP (Bước 01-06) — Ngày 1-2

**Mục tiêu:** Tạo môi trường chạy được, có DB + app khung.

| Bước | File | Việc cần làm | Cách test |
|---|---|---|---|
| 01 | `requirements.txt` | Ghi danh sách thư viện | `pip install -r requirements.txt` không lỗi |
| 02 | `.env.example` | Mẫu biến môi trường | `cp .env.example .env` chạy được |
| 03 | `.gitignore` | Loại trừ `.env`, `kms_keys/`, `pgdata/` | `git status` không thấy `.env` |
| 04 | `Dockerfile` | Build image Python | `docker build -t test .` thành công |
| 05 | `db/init.sql` | Tạo 5 bảng + 3 user + GRANT | Sau khi up, `\dt` thấy 5 bảng |
| 06 | `docker-compose.yml` | Chạy DB + App | `docker-compose up -d` → 2 container Up |

**✅ Checkpoint chặng 1:**
```bash
docker-compose up -d
docker-compose ps                          # 2 container Up
docker exec -it evoting_postgres psql -U postgres -d evoting -c "\du"
# Phải thấy: app_user, admin_app, tally_user
docker exec -it evoting_postgres psql -U admin_app -d evoting -c "SELECT * FROM votes;"
# Phải lỗi: permission denied  ✅ đúng thiết kế
```

**⚠️ Nếu chưa qua checkpoint → KHÔNG sang chặng 2.**

---

### 🟢 CHẶNG 2: CRYPTO LAYER (Bước 07-11) — Ngày 3-4

**Mục tiêu:** Mã hóa/giải mã + chữ ký số hoạt động độc lập (không cần DB).

| Bước | File | Việc cần làm | Cách test |
|---|---|---|---|
| 07 | `app/__init__.py` | File rỗng đánh dấu package | `python -c "import app"` không lỗi |
| 08 | `app/config.py` | Load `.env` thành hằng số | `python -c "from app.config import settings; print(settings.JWT_SECRET)"` |
| 09 | `app/kms.py` | Sinh RSA keypair, wrap/unwrap DEK | Chạy lần đầu → có `kms_keys/kms_private.pem` (chmod 600) |
| 10 | `app/crypto_service.py` | `encrypt_vote()` + `decrypt_vote()` | Test: encrypt rồi decrypt ra đúng plaintext |
| 11 | `app/signature_service.py` | `sign()` + `verify()` | Test: sign payload, verify OK; sửa payload, verify fail |

**✅ Checkpoint chặng 2:**
```bash
python -m tests.test_crypto
# Output:
#   ✅ Test mã hóa AES-GCM: PASS
#   ✅ Test chữ ký số RSA: PASS
#   ✅ Test sửa payload → verify fail: PASS
```

**⚠️ Nếu crypto chưa pass → KHÔNG sang chặng 3.**

---

### 🟢 CHẶNG 3: DATABASE LAYER (Bước 12-14) — Ngày 5

**Mục tiêu:** ORM mapping DB, chạy được query.

| Bước | File | Việc cần làm |
|---|---|---|
| 12 | `app/database.py` | `engine`, `SessionLocal`, `get_db()` |
| 13 | `app/models.py` | Class `Voter`, `Candidate`, `Vote`, `VoterStatus`, `UsedNonce` |
| 14 | `app/schemas.py` | Pydantic: `VoteRequest`, `RegisterRequest`, `ResultResponse` |

**✅ Checkpoint chặng 3:**
```bash
docker-compose exec app python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    n = conn.execute(text('SELECT COUNT(*) FROM candidates')).scalar()
    print(f'Có {n} đại biểu')   # Kỳ vọng: 3
"
```

---

### 🟢 CHẶNG 4: AUTH + TALLY (Bước 15-16) — Ngày 6-7

**Mục tiêu:** Đăng nhập + đếm phiếu hoạt động.

| Bước | File | Việc cần làm |
|---|---|---|
| 15 | `app/auth.py` | `hash_password`, `verify_password`, `create_jwt`, `verify_jwt` |
| 16 | `app/tally.py` | `tally_votes(db)` — đọc votes, decrypt, cộng dồn |

**✅ Checkpoint chặng 4:**
```bash
docker-compose exec app python -c "
from app.auth import create_jwt, verify_jwt
t = create_jwt('SV001')
assert verify_jwt(t) == 'SV001'
print('✅ Auth OK')

from app.database import SessionLocal
from app.tally import tally_votes
db = SessionLocal()
print('Kết quả:', tally_votes(db))   # Kỳ vọng: [{...total:0}, ...]
"
```

---

### 🟢 CHẶNG 5: API + SEED (Bước 17-18) — Ngày 8-9

**Mục tiêu:** API chạy được, seed cử tri mẫu.

| Bước | File | Việc cần làm |
|---|---|---|
| 17 | `app/seed_voters.py` | Seed 10 cử tri + sinh keypair |
| 18 | `app/main.py` | FastAPI app + 5 route: `/register`, `/login`, `/vote`, `/admin/login`, `/results` |

**✅ Checkpoint chặng 5:**
```bash
# Seed cử tri
docker-compose exec app python -m app.seed_voters
# Output: ✅ Đã tạo 10 cử tri

# Mở Swagger UI
# Truy cập http://localhost:8000/docs
# Phải thấy 5 endpoint
```

---

### 🟢 CHẶNG 6: FRONTEND (Bước 19-22) — Ngày 10

**Mục tiêu:** 4 trang HTML hoạt động end-to-end.

| Bước | File | Việc cần làm |
|---|---|---|
| 19 | `static/register.html` | Form đăng ký, lưu private key vào localStorage |
| 20 | `static/login.html` | Form login, lưu JWT vào localStorage |
| 21 | `static/vote.html` | Chọn đại biểu, ký bằng private key, gửi |
| 22 | `static/admin.html` | Xem kết quả tổng |

**✅ Checkpoint chặng 6:**
- Mở browser → đăng ký → đăng nhập → bỏ phiếu → admin xem kết quả.
- Tất cả không lỗi Console.

---

### 🟢 CHẶNG 7: TEST (Bước 23-24) — Ngày 11-12

**Mục tiêu:** Chạy script tấn công, xác nhận hệ thống chống được.

| Bước | File | Việc cần làm |
|---|---|---|
| 23 | `tests/test_crypto.py` | Test AES + RSA (không cần DB) |
| 24 | `tests/test_attack.py` | Test SQL injection, replay, double vote, đọc DB |

**✅ Checkpoint chặng 7:**
```bash
docker-compose exec app python -m tests.test_attack
# Output:
#   [1/5] SQL Injection test ............. PASS (bị chặn)
#   [2/5] Replay attack test ............. PASS (bị chặn)
#   [3/5] Double vote test ............... PASS (bị chặn)
#   [4/5] Đọc DB bằng admin_app .......... PASS (bị từ chối)
#   [5/5] Giả mạo chữ ký ................. PASS (bị từ chối)
```

---

### 🟢 CHẶNG 8: DOCS + NỘP (Bước 25-28) — Ngày 13-14

**Mục tiêu:** Viết tài liệu + quay video + nộp.

| Bước | File | Việc cần làm |
|---|---|---|
| 25 | `docs/architecture.md` | Sơ đồ kiến trúc + luồng |
| 26 | `docs/technical.md` | Giải thích cơ chế mã hóa + KMS |
| 27 | `docs/risk-analysis.md` | Rủi ro còn tồn tại |
| 28 | `README.md` | Đã có sẵn — chỉ cần điền tên nhóm |

**✅ Checkpoint chặng 8:**
- Đã có 3 file docs.
- Đã quay video demo 3 kịch bản.
- Đã nén project thành `Lab3_<TênNhóm>.zip`.
- Đã nộp.

---

## 4. Luồng xử lý chi tiết

### 4.1. Luồng khởi động hệ thống

```
User gõ: docker-compose up -d
   │
   ├─▶ Docker đọc docker-compose.yml
   │
   ├─▶ Container "postgres" start trước:
   │      ├─▶ Load image postgres:16-alpine
   │      ├─▶ Đọc biến môi trường POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
   │      ├─▶ Lần đầu: chạy db/init.sql → tạo bảng + 3 role + GRANT
   │      ├─▶ Healthcheck: pg_isready → healthy
   │      └─▶ 🟢 PostgreSQL sẵn sàng ở port 5432
   │
   └─▶ Container "app" chờ postgres healthy rồi mới start:
          ├─▶ Build image từ Dockerfile (lần đầu)
          ├─▶ Copy requirements.txt → pip install
          ├─▶ Copy source code
          ├─▶ Chạy: uvicorn app.main:app --host 0.0.0.0 --port 8000
          │      │
          │      ├─▶ Import app/config.py → load .env
          │      │      └─▶ Biến: JWT_SECRET, DATABASE_URL, ...
          │      │
          │      ├─▶ Import app/kms.py:
          │      │      ├─▶ Lần đầu: sinh RSA 2048
          │      │      ├─▶ Lưu private vào kms_keys/kms_private.pem (chmod 600)
          │      │      ├─▶ Lưu public vào kms_keys/kms_public.pem
          │      │      └─▶ Lần sau: load từ file
          │      │
          │      ├─▶ Import app/database.py → tạo engine kết nối PostgreSQL
          │      │
          │      ├─▶ Import app/models.py → map class → bảng
          │      │
          │      └─▶ Import app/main.py → đăng ký routes
          │
          └─▶ 🟢 Server sẵn sàng ở http://localhost:8000
```

---

### 4.2. Luồng đăng ký cử tri

```
[CLIENT] Cử tri mở /static/register.html
   │
   ├─▶ Điền form: voter_id = "SV001", full_name = "Nguyễn Văn X", password = "abc123"
   │
   ├─▶ Click "Đăng ký" → JS gọi POST /register
   │      │
   │      └─▶ [SERVER] Route /register trong main.py:
   │             │
   │             ├─▶ 1. Validate schema (RegisterRequest)
   │             ├─▶ 2. Check voter_id chưa tồn tại trong bảng voters
   │             ├─▶ 3. auth.hash_password("abc123") → (hash, salt)
   │             ├─▶ 4. signature_service.generate_voter_keypair() → (private_pem, public_pem)
   │             ├─▶ 5. BEGIN TRANSACTION
   │             ├─▶ 6. INSERT voters(voter_id, full_name, hash, salt, public_key)
   │             ├─▶ 7. INSERT voter_status(voter_id, has_voted=FALSE)
   │             ├─▶ 8. COMMIT
   │             └─▶ 9. Trả về { "private_key_pem": "-----BEGIN..." }
   │                    ⚠️ CHỈ TRẢ VỀ 1 LẦN DUY NHẤT
   │
   └─▶ [CLIENT] JS:
          ├─▶ Lưu private_key_pem vào localStorage["voter_private_key_SV001"]
          ├─▶ Xóa biến private_key khỏi RAM
          └─▶ Hiện: "Đăng ký thành công! Hãy lưu file backup private key."
                 + Nút "Download private key" (để backup)
```

**Tại sao private key không lưu DB?**
- Nếu server giữ → server có thể **giả mạo chữ ký** cử tri → mất Non-repudiation.
- Chỉ cử tri giữ → chỉ cử tri tạo được chữ ký → đúng nguyên tắc.

---

### 4.3. Luồng đăng nhập

```
[CLIENT] Cử tri mở /static/login.html
   │
   ├─▶ Điền voter_id + password → POST /login
   │
   └─▶ [SERVER] Route /login:
          ├─▶ 1. SELECT voters WHERE voter_id = ?
          ├─▶ 2. auth.verify_password(password, voter.password_hash, voter.salt)
          │      ├─▶ Nếu SAI → 401 Unauthorized
          │      └─▶ Nếu ĐÚNG:
          ├─▶ 3. auth.create_jwt(voter_id, is_admin=False) → token
          └─▶ 4. Trả về { "access_token": "eyJ...", "token_type": "bearer" }
```

---

### 4.4. Luồng bỏ phiếu (QUAN TRỌNG NHẤT)

```
[CLIENT] Cử tri ở /static/vote.html
   │
   ├─▶ Bấm "Bỏ phiếu cho Nguyễn Văn A" (candidate_id=1)
   │
   ├─▶ [CLIENT] Bước 1: Chuẩn bị payload
   │      │
   │      ├─▶ nonce = crypto.getRandomValues(16 byte) → hex string
   │      ├─▶ timestamp = Math.floor(Date.now() / 1000)
   │      ├─▶ payload_obj = { candidate_id: 1, nonce: "a1b2...", timestamp: 1712... }
   │      ├─▶ payload_json = JSON.stringify(payload_obj)
   │      └─▶ payload_bytes = new TextEncoder().encode(payload_json)
   │
   ├─▶ [CLIENT] Bước 2: Ký payload
   │      │
   │      ├─▶ Lấy private_key từ localStorage
   │      ├─▶ signature = RSA_sign(private_key, payload_bytes)
   │      └─▶ signature_base64 = base64(signature)
   │
   ├─▶ [CLIENT] Bước 3: Gửi request
   │      │
   │      └─▶ POST /vote
   │             Headers: { Authorization: "Bearer <JWT>" }
   │             Body: {
   │                 "payload": payload_obj,
   │                 "signature": signature_base64
   │             }
   │
   ├─▶ [SERVER] Route /vote:
   │      │
   │      │  ============ BƯỚC XÁC THỰC ============
   │      ├─▶ 1. auth.verify_jwt(token) → voter_id
   │      │       └─▶ Nếu sai → 401
   │      │
   │      ├─▶ 2. Check timestamp ≤ 5 phút:
   │      │       abs(now - payload.timestamp) > 300 → 400 "Request quá cũ"
   │      │
   │      ├─▶ 3. Check nonce chưa dùng:
   │      │       SELECT used_nonces WHERE nonce = ? → nếu có → 400 "Replay attack"
   │      │
   │      ├─▶ 4. Check candidate tồn tại:
   │      │       SELECT candidates WHERE id = ? → nếu không → 400
   │      │
   │      ├─▶ 5. Lấy public_key của voter:
   │      │       SELECT voters.public_key WHERE voter_id = ?
   │      │
   │      ├─▶ 6. Verify signature:
   │      │       RSA_verify(public_key, payload_bytes, signature)
   │      │       └─▶ Nếu FALSE → 400 "Chữ ký không hợp lệ"
   │      │
   │      │  ============ BƯỚC GHI DB ============
   │      ├─▶ 7. BEGIN TRANSACTION
   │      │
   │      ├─▶ 8. SELECT voter_status WHERE voter_id FOR UPDATE
   │      │       (khóa dòng → request khác không sửa được)
   │      │
   │      ├─▶ 9. Check status.has_voted == False:
   │      │       Nếu TRUE → ROLLBACK → 400 "Bạn đã bỏ phiếu rồi"
   │      │
   │      ├─▶ 10. Mã hóa lá phiếu:
   │      │       enc = crypto_service.encrypt_vote(payload_bytes)
   │      │       # Trong hàm encrypt_vote:
   │      │         DEK = os.urandom(32)              # AES key
   │      │         IV  = os.urandom(12)              # GCM nonce
   │      │         ciphertext, tag = AES_GCM(DEK, IV).encrypt(payload)
   │      │         wrapped_dek = kms.wrap_dek(DEK)   # RSA encrypt DEK
   │      │         del DEK                            # xóa DEK khỏi RAM
   │      │
   │      ├─▶ 11. INSERT votes(vote_id, ciphertext, wrapped_dek, iv, tag)
   │      │       ⚠️ KHÔNG có voter_id trong bảng này
   │      │
   │      ├─▶ 12. receipt_hash = SHA256(vote_id + receipt_secret)
   │      │       (cử tri giữ receipt_secret, dùng để verify sau)
   │      │
   │      ├─▶ 13. UPDATE voter_status
   │      │       SET has_voted=TRUE, receipt_hash=..., signature=..., voted_at=NOW()
   │      │
   │      ├─▶ 14. INSERT used_nonces(nonce)
   │      │
   │      └─▶ 15. COMMIT → trả về { success: true, receipt: "..." }
   │
   └─▶ [CLIENT] Hiện: "Bỏ phiếu thành công! Receipt: a1b2c3..."
                Lưu receipt vào localStorage để verify sau.
```

**Giải thích tại sao an toàn:**
- Bước 8 (`FOR UPDATE`): khóa dòng `voter_status` → 2 request đồng thời chỉ 1 cái pass.
- Bước 10: DEK sinh mới mỗi lần → cùng 1 candidate, ciphertext khác nhau.
- Bước 11: `votes` không có `voter_id` → không biết ai bầu ai.
- Bước 13: `signature` lưu ở `voter_status` (bảng riêng) → không nối với `votes`.

---

### 4.5. Luồng Admin xem kết quả

```
[CLIENT] Admin mở /static/admin.html
   │
   ├─▶ Nhập username/password → POST /admin/login
   │      │
   │      └─▶ [SERVER]:
   │             ├─▶ So khớp với ADMIN_USERNAME + ADMIN_PASSWORD trong .env
   │             ├─▶ Nếu SAI → 401
   │             └─▶ Nếu ĐÚNG → JWT với is_admin=true
   │
   ├─▶ [CLIENT] GET /results
   │      Headers: { Authorization: "Bearer <admin_token>" }
   │
   └─▶ [SERVER] Route /results:
          │
          ├─▶ 1. auth.verify_jwt(token, require_admin=True)
          │       └─▶ Nếu is_admin != True → 403 Forbidden
          │
          ├─▶ 2. Gọi tally.tally_votes(db):
          │      │
          │      ├─▶ SELECT candidate_id, name FROM candidates
          │      │       → counts = {1: {"name": "A", "total": 0}, 2: {...}, 3: {...}}
          │      │
          │      ├─▶ SELECT * FROM votes
          │      │
          │      └─▶ Với mỗi vote:
          │             ├─▶ DEK = kms.unwrap_dek(vote.wrapped_dek)   # RSA decrypt
          │             ├─▶ plaintext = AES_GCM(DEK, vote.iv).decrypt(vote.ciphertext, vote.tag)
          │             ├─▶ data = json.loads(plaintext)
          │             ├─▶ counts[data["candidate_id"]]["total"] += 1
          │             ├─▶ del DEK          # xóa khỏi RAM
          │             └─▶ del plaintext    # xóa khỏi RAM
          │
          ├─▶ 3. KHÔNG log plaintext, KHÔNG cache
          │
          └─▶ 4. Trả về:
                 {
                     "results": [
                         {"candidate_id": 1, "name": "Nguyễn Văn A", "total": 100},
                         {"candidate_id": 2, "name": "Trần Thị B",   "total": 50},
                         {"candidate_id": 3, "name": "Lê Văn C",     "total": 20}
                     ],
                     "total_votes": 170,
                     "tallied_at": "2024-01-15T10:30:00Z"
                 }
```

**Tại sao Admin không giải mã được từng phiếu?**

| Lớp phòng thủ | Cơ chế | File |
|---|---|---|
| **1. Không có key** | Private key chỉ trong class KMS, chỉ `tally.py` gọi được | `kms.py`, `tally.py` |
| **2. Không có endpoint** | Không có route `/votes/{id}` trả ciphertext hay plaintext | `main.py` |
| **3. Không có quyền DB** | `admin_app` role không có SELECT trên `votes` | `init.sql` |
| **4. Không có voter_id** | Kể cả giải mã, không biết ai bầu ai | `models.py` |
| **5. Tally batch** | Xử lý trong 1 hàm, trả aggregate, không lộ từng bước | `tally.py` |

---

### 4.6. Luồng chống Replay Attack (chi tiết)

```
Kịch bản xấu:
1. Cử tri A gửi POST /vote {payload, signature} với nonce="abc123"
2. Server xử lý OK, lưu vote, INSERT used_nonces("abc123")
3. Hacker chặn request này (MITM)
4. Hacker gửi lại Y NGUYÊN request đó 100 lần

Server xử lý từng request:
   Lần 1 (thật): OK → vote được lưu
   Lần 2 (replay): Check nonce "abc123" → ĐÃ DÙNG → 400 Replay attack
   Lần 3 (replay): Tương tự → 400
   ...
   Lần 100: 400

=> Chỉ 1 vote được lưu. Hacker thất bại.
```

**Nếu hacker sửa nonce thành "xyz789"?**
- Payload thay đổi → `signature` không còn khớp.
- Server verify signature → FALSE → 400 "Chữ ký không hợp lệ".

**Nếu hacker sửa cả nonce và tạo signature mới?**
- Hacker không có private key của cử tri → không tạo được signature.
- Server verify → FALSE → 400.

**Nếu hacker gửi sau 10 phút?**
- Timestamp cũ > 5 phút → 400 "Request quá cũ".

=> **3 lớp phòng thủ**: nonce + timestamp + signature.

---

### 4.7. Luồng chống Double Voting (chi tiết)

```
Kịch bản xấu:
1. Cử tri A mở 2 tab browser
2. Tab 1 bấm "Bỏ phiếu cho X"
3. Tab 2 bấm "Bỏ phiếu cho Y" (gần như đồng thời)

Cả 2 request đến server cùng lúc:

Request 1:
   BEGIN TRANSACTION
   SELECT voter_status WHERE voter_id='A' FOR UPDATE   ← Khóa dòng A
   Check has_voted = FALSE → OK
   INSERT vote X
   UPDATE voter_status SET has_voted=TRUE
   COMMIT → nhả khóa

Request 2:
   BEGIN TRANSACTION
   SELECT voter_status WHERE voter_id='A' FOR UPDATE   ← Chờ request 1 nhả khóa
   (sau khi request 1 commit)
   Check has_voted = TRUE → ROLLBACK
   Trả 400 "Bạn đã bỏ phiếu rồi"

=> Chỉ 1 vote được lưu.
```

**Nếu không dùng `FOR UPDATE`?**
- Cả 2 request đọc `has_voted = FALSE` cùng lúc.
- Cả 2 đều pass check → 2 votes được lưu → **DOUBLE VOTING**.

=> `FOR UPDATE` là bắt buộc.

---

## 5. Checklist theo ngày

### 📅 Ngày 1-2 — Chặng 1: Setup

- [ ] Chạy `init_project.py` tạo cấu trúc.
- [ ] Viết `requirements.txt`.
- [ ] Viết `.env.example`.
- [ ] Viết `.gitignore`.
- [ ] Viết `Dockerfile`.
- [ ] Viết `db/init.sql`.
- [ ] Viết `docker-compose.yml`.
- [ ] `cp .env.example .env` + sửa password.
- [ ] `docker-compose up -d` → 2 container Up.
- [ ] Test `psql -U admin_app` không thấy `votes`.

### 📅 Ngày 3-4 — Chặng 2: Crypto

- [ ] Viết `app/__init__.py`.
- [ ] Viết `app/config.py`.
- [ ] Viết `app/kms.py`.
- [ ] Viết `app/crypto_service.py`.
- [ ] Viết `app/signature_service.py`.
- [ ] Viết `tests/test_crypto.py`.
- [ ] Chạy test → PASS hết.

### 📅 Ngày 5 — Chặng 3: Database

- [ ] Viết `app/database.py`.
- [ ] Viết `app/models.py`.
- [ ] Viết `app/schemas.py`.
- [ ] Test query `SELECT COUNT(*) FROM candidates` → ra 3.

### 📅 Ngày 6-7 — Chặng 4: Auth + Tally

- [ ] Viết `app/auth.py`.
- [ ] Viết `app/tally.py`.
- [ ] Test JWT + tally rỗng.

### 📅 Ngày 8-9 — Chặng 5: API + Seed

- [ ] Viết `app/seed_voters.py`.
- [ ] Chạy seed → 10 cử tri.
- [ ] Viết `app/main.py` với 5 routes.
- [ ] Mở `/docs` → thấy 5 endpoint.

### 📅 Ngày 10 — Chặng 6: Frontend

- [ ] Viết `static/register.html`.
- [ ] Viết `static/login.html`.
- [ ] Viết `static/vote.html`.
- [ ] Viết `static/admin.html`.
- [ ] Test end-to-end bằng browser.

### 📅 Ngày 11-12 — Chặng 7: Test

- [ ] Viết `tests/test_attack.py`.
- [ ] Chạy script → 5/5 PASS.
- [ ] Test 3 kịch bản demo chính.

### 📅 Ngày 13-14 — Chặng 8: Docs + Nộp

- [ ] Viết `docs/architecture.md`.
- [ ] Viết `docs/technical.md`.
- [ ] Viết `docs/risk-analysis.md`.
- [ ] Cập nhật `README.md` (tên nhóm, MSSV).
- [ ] Quay video demo.
- [ ] Nén project → `Lab3_<TênNhóm>.zip`.
- [ ] Nộp bài.

---

## 🔑 Ghi nhớ 5 điểm vàng

1. **AES-256-GCM** mã hóa lá phiếu (đối xứng, nhanh).
2. **RSA-2048-OAEP** wrap chìa AES (bất đối xứng, an toàn trao đổi chìa).
3. **KMS** giữ private key — không cho ra ngoài, không log.
4. **Tách bảng** `votes` (không có voter_id) và `voter_status` (không có candidate_id).
5. **FOR UPDATE + nonce + signature** chống double vote, replay, giả mạo.

---

> **Chúc nhóm hoàn thành tốt bài lab! 🚀**
