<!--
FILE: docs/STRUCTURE.md
MỤC ĐÍCH: Bản đồ thư mục và hợp đồng triển khai thống nhất trước khi viết code.
CÁCH DÙNG: Đọc cây thư mục, hợp đồng dữ liệu, rồi mở comment đầu module.
KHI SỬA: Đổi hợp đồng thì cập nhật backend, frontend, tests và ROADMAP.md.
TRẠNG THÁI: Hướng dẫn triển khai; các module nghiệp vụ vẫn là khung.
-->

# Bản đồ cấu trúc và cách bắt đầu code

Giữ 5 bảng, 3 role DB, hai chữ ký, AES-GCM + RSA-OAEP và luồng ban đầu.
Gom backend theo chức năng: core, auth, api, database, crypto, voting.
main.py là điểm vào duy nhất ở gốc app. Giữ tên file quen thuộc, ví dụ app/auth/auth.py.
Các nhóm dùng chung mật mã/database thay vì sao chép code giữa nhóm.

## 1. Cây thư mục

```text
HeThongBauCu/
├── app/                         Backend, gom theo chức năng
│   ├── __init__.py              Package gốc
│   ├── main.py                  FastAPI, 6 endpoint, gọi các nhóm bên dưới
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            Cấu hình dùng chung
│   ├── auth/
│   │   ├── __init__.py
│   │   └── auth.py              Password hash, activation hash, JWT
│   ├── api/
│   │   ├── __init__.py
│   │   └── schemas.py           Request/response JSON của các endpoint
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py          3 engine/session và Base
│   │   ├── models.py            Mapping 5 bảng
│   │   └── seed_voters.py       Nạp cử tri và mã kích hoạt
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── kms.py               Cặp RSA của hệ thống
│   │   ├── crypto_service.py    AES-GCM và bọc khóa AES
│   │   └── signature_service.py Chuẩn hóa và kiểm tra chữ ký cử tri
│   └── voting/
│       ├── __init__.py
│       ├── voting_service.py    Transaction bỏ phiếu
│       └── tally.py             Kiểm phiếu, trả tổng
├── static/                      Giao diện hiện là khung hướng dẫn
│   ├── register.html           Tên cũ, chức năng là kích hoạt /activate
│   ├── login.html              Đăng nhập cử tri
│   ├── vote.html               Chọn, ký và gửi phiếu
│   ├── admin.html              Đăng nhập admin, xem tổng
│   └── js/
│       └── crypto.js           MỚI: helper khóa/chữ ký trong browser
├── db/
│   ├── 01_roles.sh             Đã có script tạo 3 role từ biến môi trường
│   └── init.sql                Đã có bảng, constraint, mẫu ứng viên, quyền
├── tests/                      Khung, chưa có test nghiệp vụ thực thi
│   ├── __init__.py             MỚI: package tests
│   ├── test_crypto.py          Mật mã/password/JWT, không cần DB
│   ├── test_attack.py          API và quyền DB trên môi trường test
│   └── test_voting.py          MỚI: rollback, bầu đồng thời, quyền INSERT
├── docs/
│   ├── STRUCTURE.md            Bạn đang đọc
│   ├── architecture.md         Khung viết tài liệu kiến trúc
│   ├── technical.md            Khung viết giải thích kỹ thuật
│   ├── risk-analysis.md        Khung viết giới hạn/rủi ro
│   ├── Luong_du_lieu_he_thong_bau_cu.md
│   ├── Luong_du_lieu_he_thong_bau_cu.docx
│   └── build_flow_docx.py      Script xuất Word đã có code
├── .env                        Cấu hình riêng, không đưa Git; không sửa lần này
├── .env.example                Mẫu cấu hình, có ELECTION_ID
├── .gitignore                  Quy tắc riêng cho Git
├── .gitattributes              Giữ LF cho script shell chạy trong container
├── docker-compose.yml          Chỉ PostgreSQL, localhost:5432, volume pgdata
├── requirements.txt            Dependency hiện có, chưa nâng phiên bản
├── README.md                   Trạng thái dự án và điểm bắt đầu
└── ROADMAP.md                  Thứ tự thực hành và kiểm tra từng chặng
```

Không cần thêm repositories/, controllers/, routers/ lúc này: 6 route và các service đã đủ tách nhiệm vụ.
venv/ là thư viện đã cài, không sửa comment trong đó. .git/ là metadata Git.
File Word là đầu ra nhị phân; hướng dẫn nằm trong Markdown nguồn và script xuất Word.

## 2. Cách đọc comment mỗi file

Mỗi khung có: MỤC ĐÍCH → PHỤ THUỘC → CÁCH TRIỂN KHAI THEO THỨ TỰ → TỰ KIỂM TRA.
Viết code dưới docstring/comment. Tên hàm là giao ước dự kiến, chưa tồn tại.
File cấu hình/SQL đã có nội dung thì đọc hướng dẫn trước khi thay đổi chức năng.

## 3. Quan hệ gọi hàm

```text
app/main.py
  ├─ auth/auth.py                 Xác minh người gọi
  ├─ api/schemas.py               Hợp đồng HTTP JSON
  ├─ database/database.py         Session và transaction
  ├─ database/models.py           Dữ liệu activate/login/candidates
  ├─ voting/voting_service.py     Nghiệp vụ bỏ phiếu
  │    ├─ crypto/signature_service.py
  │    ├─ crypto/crypto_service.py → crypto/kms.py
  │    └─ database/models.py
  └─ voting/tally.py → crypto/crypto_service.py → crypto/kms.py

register.html và vote.html → static/js/crypto.js
Mọi nhóm cần cấu hình → core/config.py
```

Service không import main. schemas không cần import models. Không kết nối DB hoặc sinh khóa khi import package.

## 4. Giao ước dữ liệu giữa frontend và backend

| Endpoint | Request | Response chính | DB |
| --- | --- | --- | --- |
| POST /activate | voter_id, activation_code, password, public_key | success | UPDATE voters, INSERT voter_status |
| POST /login | voter_id, password | access_token, token_type, election_id | Chỉ đọc voters |
| GET /candidates | Không body | Danh sách candidate_id, name, party | Đọc candidates |
| POST /vote | ballot, sig_ballot, sig_cast; Bearer JWT | success, receipt hex | INSERT used_nonces/votes; UPDATE voter_status |
| POST /admin/login | username, password | access_token, token_type | Đọc cấu hình, không có bảng admin |
| GET /results | Bearer JWT admin | results, total_votes | Tally đọc votes/candidates |

### Payload và chữ ký

```text
ballot = {candidate_id: int, nonce: hex32, ts: Unix seconds integer}
cast   = {election_id: string, voter_id: string, nonce: hex32, ts: integer}
```

- ELECTION_ID đọc từ .env của backend local, trả cho cử tri khi login; backend dựng lại cast bằng ID này.
- Hai thông điệp dùng chung nonce/ts. Server lấy voter_id từ JWT, không nhận danh tính tùy ý từ body.
- Dữ liệu ký: JSON phẳng, keys sắp xếp tăng dần, không khoảng trắng, UTF-8; không có extra fields.
- ID chỉ ASCII; ts là số nguyên an toàn trong JavaScript, không float/bool. Tránh khác biệt serialize giữa hai ngôn ngữ.
- RSA-PSS 2048, SHA-256, MGF1 SHA-256, salt length 32 byte cả Python và JavaScript.
- Public key: SPKI PEM. Private backup: PKCS8, giữ phía người dùng. Chữ ký qua HTTP: Base64 chuẩn.
- Receipt: SHA-256 trên bytes sig_cast đã decode; DB lưu bytes, response trả hex. Không hash chuỗi Base64 thay thế.
- sig_ballot trong envelope là Base64 để serialize JSON; sig_cast trong voter_status là BYTEA.

### Mật khẩu và activation code

Chọn PBKDF2-HMAC-SHA256 theo khung app/auth/auth.py và dependency cryptography sẵn có.
Salt ngẫu nhiên ở voters.salt; password_hash chứa phiên bản, iterations và digest dạng bytes tự mô tả.
Hiệu chỉnh iterations trước sử dụng thật; verify dùng tham số của hash đã lưu, không phụ thuộc cấu hình mới.
Tài liệu cũ ghi nhiều lựa chọn Argon2id/bcrypt/PBKDF2; bản này chốt một hướng để triển khai nhất quán.
Không dùng SHA-256 đơn thuần cho mật khẩu. Activation code ngẫu nhiên đủ dài có thể lưu SHA-256(code).

### Mã hóa phiếu

```text
envelope = {ballot, sig_ballot}
plaintext = JSON envelope dưới dạng UTF-8 bytes
encrypt_vote → {ciphertext: bytes, wrapped_dek: bytes, iv: bytes, tag: bytes}
```

Mỗi phiếu có DEK 32 byte mới, IV 12 byte mới; AES-GCM tag 16 byte.
RSA-OAEP bọc DEK với SHA-256/MGF1 SHA-256/label=None; cặp RSA KMS khác cặp RSA cử tri.
Không có cột voter_id, candidate_id, nonce, timestamp hoặc receipt riêng trong votes.
Nonce/ts/candidate vẫn nằm trong envelope mã hóa theo thiết kế gốc.

## 5. Ai sở hữu transaction?

main mở `with session.begin()` trước truy vấn DB của thao tác activate/vote.
Dependency xác minh JWT không truy vấn DB trên session đó trước khi begin.
voting_service nhận session, thực hiện SELECT FOR UPDATE/INSERT/UPDATE; không tự commit.
main chỉ trả success sau khi context commit; bắt lỗi bên ngoài context.

```text
BEGIN
  Kiểm tra voter, candidate, chữ ký, thời gian
  SELECT voter_status FOR UPDATE → chưa bầu?
  INSERT used_nonces
  Mã hóa phiếu
  INSERT votes (Core inline, UUID v4 tự sinh, không RETURNING)
  UPDATE voter_status
COMMIT → trả receipt

Bất kỳ lỗi trước commit → ROLLBACK cả ba thay đổi
```

Chỉ khóa chính voter_status không đủ tự chống bầu hai lần; phải kiểm tra has_voted dưới khóa dòng.
Kích hoạt cũng khóa voters để tránh hai request thay khóa/password và tạo trạng thái cùng lúc.

## 6. Giới hạn phải ghi rõ trong tài liệu

Đây là demo một cuộc bầu cử. ELECTION_ID trong chữ ký không biến schema thành hệ thống nhiều cuộc bầu cử.
Backend thấy lựa chọn trước mã hóa và tiếp cận khóa KMS trong KMS_KEY_DIR (dự kiến ./kms_keys khi chạy local).
Tách bảng giảm liên kết trực tiếp, không chứng minh ẩn danh tuyệt đối: sau giải mã, nonce/ts/chữ ký có thể giúp liên kết khi có thêm dữ liệu.
sig_cast và receipt chưa phải bằng chứng kiểm phiếu đầu-cuối; schema chưa lưu đủ cast message để kiểm tra độc lập sau này.
Storage khóa browser demo có rủi ro XSS; không có cơ chế mất khóa/khôi phục tự động.
Cần code, test và rà soát dependency/TLS/quyền vận hành trước sử dụng thật.

## 7. File bổ sung và lý do

| File | Lý do |
| --- | --- |
| .gitattributes | Tránh Windows checkout script shell thành CRLF |
| app/voting/voting_service.py | Tách transaction bỏ phiếu khỏi HTTP để dễ đọc và kiểm thử |
| static/js/crypto.js | Hai trang dùng cùng cách tạo khóa và ký, tránh lệch giao thức |
| tests/__init__.py | Chạy test qua package unittest |
| tests/test_voting.py | Kiểm tra đồng thời và rollback bằng PostgreSQL thật |
| docs/STRUCTURE.md | Tra cây thư mục và hợp đồng xuyên suốt |


## 8. Import và lệnh chạy sau khi gom thư mục

Đây là mẫu import để dùng khi đã viết các hàm/lớp tương ứng; hiện các module vẫn chỉ là khung.
Thư mục auth và file auth.py là hai cấp: không dùng `from app.auth import hash_password`
khi __init__.py chưa export hàm đó. Dùng đường dẫn đầy đủ như sau:

```python
from app.core.config import get_settings
from app.auth.auth import hash_password, verify_password, verify_jwt
from app.api.schemas import VoteRequest
from app.database.database import Base, AppSession, TallySession
from app.database.models import Voter, Vote, VoterStatus
from app.crypto.kms import KMS
from app.crypto.crypto_service import encrypt_vote, decrypt_vote
from app.crypto.signature_service import verify_signature
from app.voting.voting_service import cast_vote
from app.voting.tally import tally_votes
```

Chạy từ thư mục gốc dự án, không chạy trực tiếp đường dẫn file Python con:

```powershell
# Sau khi code tương ứng hoàn thành
python -m app.database.seed_voters
uvicorn app.main:app --reload
python -m unittest tests.test_crypto
```

Docker hiện chỉ chạy PostgreSQL; dùng `docker compose up -d`, không build/mount app hoặc static.
Sau khi viết backend, chạy `uvicorn app.main:app --reload` trên máy local.
DB URL dùng 127.0.0.1:5432/evoting; KMS_KEY_DIR dùng ./kms_keys, không có volume KMS trong Compose hiện tại.
Không giữ các file wrapper ở đường dẫn cũ để tránh hai nơi có cùng chức năng.
