-- FILE: db/init.sql
-- MỤC ĐÍCH: Nguồn chuẩn tạo 5 bảng, dữ liệu ứng viên và GRANT; đã có SQL.
-- CÁCH DÙNG / VIỆC CẦN LÀM:
-- 1. Đọc lần lượt voters, candidates, votes, voter_status, used_nonces rồi phần GRANT.
-- 2. Giữ votes không có voter_id/timestamp; voter_status không có candidate_id.
-- 3. SQL chỉ chạy tự động khi volume PostgreSQL mới; sửa file không tự đổi DB đang có.
-- 4. Nếu đổi schema sau này phải viết migration; không xóa volume có dữ liệu thật.
-- 5. 01_roles.sh phải chạy trước. App tự tạo UUID, INSERT inline không RETURNING.
-- ĐỌC KÈM: docs/STRUCTURE.md

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- PHẦN 1: BẢNG
-- ============================================================

-- ---------- Cử tri ----------
-- Danh sách được nạp sẵn (seed). Cử tri "kích hoạt" sau bằng activation code.
-- KHÔNG chứa private key. public_key do trình duyệt sinh và gửi lên lúc kích hoạt.
CREATE TABLE voters (
    voter_id        VARCHAR(20)  PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    activation_hash BYTEA,                       -- hash mã kích hoạt; xóa (NULL) sau khi dùng
    activated       BOOLEAN      NOT NULL DEFAULT FALSE,
    password_hash   BYTEA,                       -- NULL tới khi kích hoạt
    salt            BYTEA,                       -- NULL nếu dùng bcrypt/argon2 (salt nằm trong hash)
    public_key      TEXT,                        -- RSA public key (PEM), NULL tới khi kích hoạt
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_voter_activated CHECK (
        activated = FALSE OR (password_hash IS NOT NULL AND public_key IS NOT NULL)
    )
);

-- ---------- Đại biểu ----------
CREATE TABLE candidates (
    -- SERIAL = INTEGER + SEQUENCE + DEFAULT nextval(...) + NOT NULL
    candidate_id  SERIAL       PRIMARY KEY, 
    name          VARCHAR(100) NOT NULL,
    party         VARCHAR(50)
);

-- ---------- Phiếu bầu ----------
-- ⚠️ KHÔNG có voter_id. KHÔNG có timestamp (cột thời gian + voter_status.voted_at
--    sẽ cho phép nối cử tri với phiếu). vote_id là UUID ngẫu nhiên.
-- Ứng dụng phải TỰ SINH UUID (uuid.uuid4()) khi INSERT để không cần RETURNING,
-- vì app_user chỉ có quyền INSERT (không SELECT) trên bảng này.
CREATE TABLE votes (
    vote_id      UUID   PRIMARY KEY DEFAULT gen_random_uuid(),
    ciphertext   BYTEA  NOT NULL,                -- AES-GCM ciphertext (đã tách tag)
    wrapped_dek  BYTEA  NOT NULL,                -- DEK được RSA-OAEP wrap bằng public key của KMS
    iv           BYTEA  NOT NULL,
    tag          BYTEA  NOT NULL,
    CONSTRAINT chk_iv_len  CHECK (octet_length(iv)  = 12),
    CONSTRAINT chk_tag_len CHECK (octet_length(tag) = 16)
);

-- ---------- Trạng thái cử tri ----------
-- Chống double voting (PK = Unique Constraint) + Non-repudiation.
-- ⚠️ KHÔNG có candidate_id. sig_cast là chữ ký trên {election_id, voter_id, nonce, ts}
--    — KHÔNG chứa lựa chọn, nên không thể dò ra cử tri bầu cho ai.
CREATE TABLE voter_status (
    voter_id      VARCHAR(20) PRIMARY KEY REFERENCES voters(voter_id),
    has_voted     BOOLEAN     NOT NULL DEFAULT FALSE,
    sig_cast      BYTEA,
    receipt_hash  BYTEA,                         -- SHA-256(sig_cast); KHÔNG liên quan vote_id
    voted_at      TIMESTAMPTZ,                   -- app làm tròn theo giờ: date_trunc('hour', now())
    CONSTRAINT chk_voted_has_proof CHECK (
        has_voted = FALSE OR (sig_cast IS NOT NULL AND receipt_hash IS NOT NULL AND voted_at IS NOT NULL)
    )
);

-- ---------- Nonce đã dùng (chống replay) ----------
-- Chống trùng bằng PK: INSERT trong cùng transaction; trùng -> lỗi -> ROLLBACK.
CREATE TABLE used_nonces (
    nonce    VARCHAR(64) PRIMARY KEY,
    used_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_used_nonces_used_at ON used_nonces(used_at);

-- ============================================================
-- PHẦN 2: DỮ LIỆU MẪU
-- ============================================================
INSERT INTO candidates (name, party) VALUES
    ('Nguyễn Văn A', 'Đảng X'),
    ('Trần Thị B',   'Đảng Y'),
    ('Lê Văn C',     'Đảng Z');
-- Cử tri được seed bằng app/database/seed_voters.py (sinh mã kích hoạt, lưu hash).

-- ============================================================
-- PHẦN 3: GRANT (Least Privilege)
-- Role + schema USAGE đã được db/01_roles.sh tạo/cấp. Chỉ cấp quyền bảng ở đây.
-- ============================================================

-- app_user: ứng dụng bỏ phiếu. KHÔNG DELETE, KHÔNG đọc được votes.
GRANT SELECT, INSERT ON voters TO app_user;                      -- INSERT: cho seed_voters
GRANT UPDATE (activation_hash, activated, password_hash, salt, public_key)
                      ON voters TO app_user;                     -- chỉ cột cần cho bước kích hoạt
GRANT SELECT          ON candidates   TO app_user;
GRANT INSERT          ON votes        TO app_user;               -- chỉ ghi, không đọc lại
GRANT SELECT, INSERT, UPDATE ON voter_status TO app_user;        -- FOR UPDATE cần quyền UPDATE
GRANT INSERT          ON used_nonces  TO app_user;

-- admin_app: Admin chỉ ĐỌC (read-only), không UPDATE/DELETE, không thấy votes/voter_status/voters.
GRANT SELECT ON candidates TO admin_app;

-- tally_user: chỉ đọc votes + candidates để đếm.
GRANT SELECT ON votes      TO tally_user;
GRANT SELECT ON candidates TO tally_user;

-- Không GRANT gì cho PUBLIC. Không ai (ngoài postgres sở hữu bảng) có UPDATE/DELETE trên votes.