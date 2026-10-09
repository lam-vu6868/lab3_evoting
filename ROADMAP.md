<!--
FILE:        ROADMAP.md
BƯỚC:        (tài liệu bổ trợ — không tính vào 28 bước code)
MỤC ĐÍCH:    Lộ trình từng chặng + luồng xử lý chi tiết
PHỤ THUỘC:   README.md
BƯỚC TIẾP:   Bắt đầu code theo Bước 01
-->

# 🗺️ ROADMAP — Lộ trình làm Lab 3

> Đọc từ trên xuống. Không nhảy chặng. Commit Git sau mỗi chặng.

## Mục lục
1. [Tổng quan](#1-tổng-quan)
2. [Phụ thuộc giữa các file](#2-phụ-thuộc-giữa-các-file)
3. [Chi tiết 8 chặng](#3-chi-tiết-8-chặng)
4. [Luồng xử lý](#4-luồng-xử-lý)
5. [Checklist theo ngày](#5-checklist-theo-ngày)

---

## 1. Tổng quan

28 bước chính + 3 file bổ sung làm trong Chặng 1 (`.dockerignore`, `docker-compose.dev.yml`, `db/01_roles.sh`).

```
CHẶNG 1: SETUP            (01-06 + 3 file bổ sung)  Ngày 1-2
CHẶNG 2: CRYPTO LAYER     (07-11)                   Ngày 3-4
CHẶNG 3: DATABASE LAYER   (12-14)                   Ngày 5
CHẶNG 4: AUTH + TALLY     (15-16)                   Ngày 6-7
CHẶNG 5: API + SEED       (17-18)                   Ngày 8-9
CHẶNG 6: FRONTEND         (19-22)                   Ngày 10
CHẶNG 7: TEST             (23-24)                   Ngày 11-12
CHẶNG 8: DOCS + NỘP       (25-28)                   Ngày 13-14
```

---

## 2. Phụ thuộc giữa các file

```
CHẶNG 1: requirements.txt, .env.example, .gitignore, .dockerignore, Dockerfile,
         db/01_roles.sh, db/init.sql  ──▶ docker-compose.yml (+ .dev.yml)
CHẶNG 2: __init__ ─ config ─┬─▶ kms ─▶ crypto_service
                            └─▶ signature_service
CHẶNG 3: database ─▶ models ─▶ schemas
CHẶNG 4: auth ; tally (cần models + kms + crypto_service)
CHẶNG 5: seed_voters ; main (gom tất cả)
CHẶNG 6: register.html / login.html / vote.html / admin.html
CHẶNG 7: test_crypto / test_attack
CHẶNG 8: docs/*.md + README
```

---

## 3. Chi tiết 8 chặng

### 🟢 CHẶNG 1 — SETUP (Bước 01-06)

| Bước | File | Việc | Test |
|---|---|---|---|
| 01 | `requirements.txt` | Ghim thư viện (JWT: PyJWT hoặc python-jose ≥ 3.4.0) | `pip install -r` OK |
| 02 | `.env.example` | Mẫu biến môi trường | `cp` được |
| 03 | `.gitignore` (+ `.dockerignore`) | Loại `.env`, `kms_keys/`, `pgdata/` | `git status` không thấy `.env` |
| 04 | `Dockerfile` | Image non-root | `docker build` OK |
| 05 | `db/01_roles.sh` + `db/init.sql` | Role từ env; 5 bảng + GRANT (không CREATE ROLE trong init.sql) | `\du`, `\dt` |
| 06 | `docker-compose.yml` (+ `.dev.yml`) | DB + App | 2 container Up |

**Checkpoint:**
```bash
docker compose up -d --build
docker compose ps                                   # 2 container Up
docker compose exec postgres psql -U postgres -d evoting -c "\du"
# thấy: app_user, admin_app, tally_user
docker compose exec postgres psql -U admin_app -d evoting -c "SELECT * FROM votes;"
# phải lỗi: permission denied  ✅
nc -zv localhost 5432                                # phải KHÔNG kết nối được (cấu hình chính)
```

### 🟢 CHẶNG 2 — CRYPTO (Bước 07-11)

| Bước | File | Việc |
|---|---|---|
| 07 | `app/__init__.py` | Rỗng |
| 08 | `app/config.py` | Load env |
| 09 | `app/kms.py` | Sinh/nạp RSA; `wrap_dek()` chỉ dùng public key; `unwrap_dek()` chỉ nạp private key khi gọi (lazy) |
| 10 | `app/crypto_service.py` | `encrypt_vote()` / `decrypt_vote()` (AES-GCM, IV 12B ngẫu nhiên) |
| 11 | `app/signature_service.py` | `verify()` RSA-PSS (hoặc PKCS1v15) với public key cử tri |

**Checkpoint** (script tạm, vì `tests/test_crypto.py` làm ở Chặng 7):
```bash
docker compose exec app python -c "
from app.crypto_service import encrypt_vote, decrypt_vote
e = encrypt_vote(b'{\"candidate_id\":1}')
assert decrypt_vote(e) == b'{\"candidate_id\":1}'
e2 = encrypt_vote(b'{\"candidate_id\":1}')
assert e['ciphertext'] != e2['ciphertext']   # IV/DEK khác nhau
print('Crypto OK')"
```

### 🟢 CHẶNG 3 — DATABASE (Bước 12-14)

| Bước | File | Lưu ý |
|---|---|---|
| 12 | `database.py` | 3 engine: `app`, `admin`, `tally` (3 URL khác nhau) |
| 13 | `models.py` | `Voter`(voter_id PK, hash, public_key, `activation_hash`, `activated`), `Candidate`, `Vote`(**UUID ngẫu nhiên**, ciphertext, wrapped_dek, iv, tag — **không voter_id, không created_at**), `VoterStatus`(voter_id **PK**, has_voted, `sig_cast`, `receipt_hash`, `voted_at` làm tròn theo giờ), `UsedNonce`(nonce **PK**) |
| 14 | `schemas.py` | Pydantic |

### 🟢 CHẶNG 4 — AUTH + TALLY (Bước 15-16)

- `auth.py`: băm mật khẩu bằng argon2id/bcrypt; JWT có `exp`; `verify_jwt(require_admin)`.
- `tally.py`: **chỉ chạy khi `now ≥ ELECTION_END`**; đọc `votes` bằng `tally_user`, xáo trộn thứ tự, giải mã trong RAM, trả aggregate, không log plaintext.

### 🟢 CHẶNG 5 — API + SEED (Bước 17-18)

Routes: `POST /activate`, `POST /login`, `GET /candidates`, `POST /vote`, `POST /admin/login`, `GET /results` (6 route).
`seed_voters.py`: nạp 10 cử tri + **mã kích hoạt dùng 1 lần** (lưu hash), in mã ra console.

### 🟢 CHẶNG 6 — FRONTEND (Bước 19-22)

- `register.html`: nhập voter_id + mã kích hoạt + mật khẩu; **WebCrypto sinh keypair trong browser**, gửi **public key**, giữ private key local + nút backup.
- `vote.html`: tạo nonce/timestamp, ký 2 chữ ký (xem 4.4), gửi.

### 🟢 CHẶNG 7 — TEST (Bước 23-24)
`test_crypto.py` (AES, RSA, sửa payload) và `test_attack.py` (SQLi, replay, double vote đồng thời, `admin_app` đọc `votes`, giả chữ ký, vote ngoài thời gian).

### 🟢 CHẶNG 8 — DOCS + NỘP (Bước 25-28)
`architecture.md`, `technical.md` (giải thích "Admin chỉ thấy tổng"), `risk-analysis.md` (1-2 trang, lấy từ README mục 9), README; quay video demo 3 kịch bản; nén `Lab3_<TênNhóm>.zip` **không kèm `.env`, `pgdata`, key**.

---

## 4. Luồng xử lý

### 4.1. Khởi động
```
docker compose up -d
 ├─ postgres: lần đầu chạy db/01_roles.sh (tạo role từ env) → db/init.sql (bảng + GRANT) → healthy
 └─ app (chờ healthy): config → kms (nạp/sinh RSA trong volume kms_keys) → database → main
```

### 4.2. Kích hoạt cử tri
```
[Browser] nhập voter_id + activation_code + password
   ├─ WebCrypto sinh keypair RSA (private KHÔNG rời browser)
   └─ POST /activate { voter_id, activation_code, password, public_key }
[Server]
   1. voter có trong danh sách và chưa activated? (không thì 400)
   2. verify activation_code (so hash) → vô hiệu hóa mã
   3. hash password; lưu public_key; activated = TRUE; tạo voter_status(has_voted=FALSE)
   4. Trả OK (không trả private key — server chưa từng có nó)
```
*Vì sao:* server không giữ private key ⇒ không thể giả chữ ký cử tri ⇒ Non-repudiation đúng nghĩa.

### 4.3. Đăng nhập
`POST /login` → verify mật khẩu → JWT (có `exp`) → trả `access_token`.

### 4.4. Bỏ phiếu (quan trọng nhất)

```
[Browser]
  nonce = 16 byte ngẫu nhiên (hex); ts = unix time
  ballot  = { candidate_id, nonce, ts }
  cast    = { election_id, voter_id, nonce, ts }          ← KHÔNG có candidate
  sig_ballot = Sign(priv, ballot)
  sig_cast   = Sign(priv, cast)
  POST /vote  (Bearer JWT)  { ballot, sig_ballot, sig_cast }

[Server — xác thực]
  1. verify_jwt → voter_id
  2. ELECTION_START ≤ now ≤ ELECTION_END, nếu không → 400
  3. |now − ts| ≤ 300s, nếu không → 400 "Request quá cũ"
  4. candidate_id tồn tại
  5. public_key của voter → verify sig_ballot và sig_cast, sai → 400

[Server — ghi DB, 1 transaction]
  6. BEGIN
  7. SELECT voter_status WHERE voter_id=? FOR UPDATE
  8. has_voted = TRUE → ROLLBACK, 400 "Bạn đã bỏ phiếu rồi"
  9. INSERT used_nonces(nonce)            ← PK; trùng → lỗi → ROLLBACK (replay)
 10. envelope = { ballot, sig_ballot } → encrypt_vote():
        DEK = random 32B; IV = random 12B
        (ct, tag) = AES-GCM(DEK, IV).encrypt(envelope)
        wrapped_dek = RSA-OAEP(KMS.public_key, DEK); xóa DEK
 11. INSERT votes(uuid_ngẫu_nhiên, ct, wrapped_dek, iv, tag)   ← KHÔNG voter_id/timestamp
 12. receipt = SHA256(sig_cast)           ← KHÔNG liên quan vote_id
 13. UPDATE voter_status SET has_voted=TRUE, sig_cast=…, receipt_hash=…, voted_at=date_trunc('hour', now())
 14. COMMIT → { success, receipt }
```

**Vì sao giữ được ẩn danh:**
- `votes` không có `voter_id`, không có timestamp, id là UUID ngẫu nhiên (không đoán thứ tự).
- Thứ duy nhất lưu cùng `voter_id` là `sig_cast` — **không chứa candidate**, nên không thể thử 3 đại biểu để kiểm chữ ký.
- `sig_ballot` (có candidate) nằm **bên trong** ciphertext, chỉ KMS mới mở được.
- `receipt` suy từ `sig_cast`, không dính `vote_id`.

> ❌ Thiết kế cũ sai ở đây: lưu chữ ký **trên payload có candidate_id** cạnh `voter_id`, và `receipt_hash = SHA256(vote_id + …)` ⇒ có thể nối cử tri với phiếu và dò ra lựa chọn.

### 4.5. Admin xem kết quả
```
POST /admin/login (so ADMIN_USERNAME/PASSWORD từ env; nên so sánh hằng-thời-gian) → JWT is_admin
GET  /results   → verify_jwt(require_admin) → 403 nếu không phải admin
                → nếu now < ELECTION_END → 403 "Cuộc bầu cử chưa kết thúc"
                → tally_votes(): đọc votes (tally_user), xáo trộn, unwrap DEK, giải mã trong RAM,
                  cộng dồn, xóa DEK/plaintext → trả { results[], total_votes }
```

| Lớp phòng thủ | Cơ chế |
|---|---|
| Không có khóa | Private key nằm trong KMS, chỉ `tally.py` nạp |
| Không có endpoint | Không có route trả từng phiếu |
| Không có quyền DB | `admin_app` không SELECT được `votes` |
| Không nối được cử tri | Không voter_id/timestamp trong `votes` |
| Không xem sớm | `/results` khóa tới `ELECTION_END` |

> ⚠️ Giới hạn: ai kiểm soát container `app` (có private key) vẫn giải mã được từng phiếu → ghi vào risk analysis.

### 4.6. Chống Replay
Request bị chặn bắt và gửi lại: lần 2 trở đi lỗi vì `nonce` đã nằm trong `used_nonces` (PK) → ROLLBACK. Đổi nonce → chữ ký sai. Gửi sau 5 phút → timestamp quá cũ. Chống trùng **bằng PK/INSERT trong transaction**, không dùng "SELECT rồi mới INSERT" (có khe race).

### 4.7. Chống Double Voting
Hai request song song: request 1 `FOR UPDATE` khóa dòng, bầu xong `COMMIT`. Request 2 chờ, thấy `has_voted = TRUE` → 400. Không có `FOR UPDATE` thì cả hai cùng đọc FALSE → bầu 2 lần. `voter_status.voter_id` là PK đóng vai Unique Constraint ở tầng DB.

---

## 5. Checklist theo ngày

**Ngày 1-2 (Setup):** requirements, .env.example, .gitignore, .dockerignore, Dockerfile, 01_roles.sh, init.sql, compose → `up` OK → `admin_app` đọc `votes` bị từ chối → port 5432 không mở ra ngoài.
**Ngày 3-4 (Crypto):** `__init__`, config, kms, crypto_service, signature_service → chạy checkpoint inline.
**Ngày 5 (DB):** database, models, schemas → `COUNT(*) FROM candidates` = 3.
**Ngày 6-7 (Auth + Tally):** auth, tally → JWT + tally rỗng OK.
**Ngày 8-9 (API + Seed):** seed_voters, main → `/docs` thấy 6 endpoint.
**Ngày 10 (Frontend):** 4 trang chạy end-to-end, không lỗi Console.
**Ngày 11-12 (Test):** test_crypto, test_attack → 5/5 PASS; quay thử 3 kịch bản.
**Ngày 13-14 (Docs + Nộp):** architecture, technical, risk-analysis, README (điền tên) → video → zip (không `.env`, `pgdata`, key) → nộp.

---

## 🔑 5 điểm vàng
1. **Hybrid**: AES-256-GCM cho phiếu, RSA-OAEP wrap khóa AES.
2. **Lúc bầu chỉ dùng public key**; private key chỉ nạp khi kiểm phiếu.
3. **Tách bảng**: `votes` (không voter_id/timestamp), `voter_status` (không candidate; chữ ký không chứa candidate).
4. **Keypair cử tri sinh ở browser** → chống chối bỏ đúng nghĩa.
5. **FOR UPDATE + nonce PK + timestamp + chữ ký** chống double vote, replay, giả mạo.