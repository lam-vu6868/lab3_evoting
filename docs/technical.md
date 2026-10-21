<!--
MỤC ĐÍCH: Giải thích payload, chữ ký, mã hóa, transaction và receipt đang dùng.
PHỤ THUỘC: docs/STRUCTURE.md, db/init.sql, app/crypto/, app/voting/ và static/js/crypto.js.
LUỒNG: Dữ liệu browser → kiểm chữ ký → mã hóa envelope → ghi DB → giải mã để đếm.
TỰ KIỂM TRA: Đối chiếu tests/test_crypto.py, tests/test_voting.py, tests/test_tally.py.
-->

# Giao thức kỹ thuật của bản demo

Ví dụ xuyên suốt: cử tri `SV001` chọn ứng viên `2`. Browser tạo nonce 16 byte ngẫu nhiên
(32 ký tự hex) và `ts` là Unix seconds dạng số nguyên. Sau đăng nhập, backend trả
`election_id`; browser dùng nó để ký đúng cuộc bầu cử.

## Hai nội dung được ký

```json
ballot = {"candidate_id":2,"nonce":"<32 ký tự hex>","ts":<Unix seconds>}
cast = {"election_id":"<mã cuộc bầu cử>","voter_id":"SV001","nonce":"<cùng nonce>","ts":<cùng ts>}
```

Mỗi object được chuẩn hóa thành JSON UTF-8: key sắp xếp tăng dần, không có khoảng trắng
thừa hoặc field ngoài hợp đồng. Browser ký riêng `ballot` và `cast` bằng private key
cử tri RSA-PSS 2048, SHA-256, MGF1 SHA-256, salt dài 32 byte; HTTP gửi hai chữ ký
Base64 cùng `ballot`. Backend lấy `voter_id` từ JWT, dựng lại `cast`, đọc public key
SPKI PEM từ `voters.public_key`, giải mã Base64 và xác minh cả hai chữ ký.
Định dạng được chốt trong [STRUCTURE.md](STRUCTURE.md) và thực hiện ở
[signature_service.py](../app/crypto/signature_service.py),
[crypto.js](../static/js/crypto.js).

## Mã hóa và bảng lưu

Backend tạo `envelope = {ballot, sig_ballot}` rồi chuyển thành JSON UTF-8. Mỗi lần
gọi `encrypt_vote` sinh khóa AES 32 byte (DEK) và IV 12 byte mới. AES-256-GCM
mã hóa envelope; tag 16 byte được tách khỏi ciphertext. Public key RSA của KMS mô phỏng
bọc DEK bằng RSA-OAEP SHA-256/MGF1 SHA-256, `label=None`.

`votes` nhận `vote_id` UUID v4 cùng `ciphertext`, `wrapped_dek`, `iv`, `tag`.
Private key KMS chỉ dùng khi kiểm phiếu để mở DEK; private key cử tri không vào backend.
Lỗi tag hoặc khóa làm kiểm phiếu dừng, không trả plaintext một phần.
`KMS_KEY_DIR` phải được giữ qua các lần khởi động; thay private key làm phiếu cũ
không thể giải mã.

## Transaction bỏ phiếu và biên nhận

`/vote` chỉ làm việc trong khoảng `[ELECTION_START, ELECTION_END)` và từ chối `ts`
cách thời gian server hơn `VOTE_REQUEST_MAX_AGE_SECONDS` (mặc định 300 giây).
Route mở một transaction; service kiểm tra cử tri/ứng viên/chữ ký, khóa dòng
`voter_status FOR UPDATE`, kiểm `has_voted`, rồi INSERT `used_nonces` và `votes`,
UPDATE `voter_status`. Mọi lỗi trước commit làm rollback cả ba thay đổi.
Phiếu được INSERT bằng Core inline, không dùng RETURNING vì `app_user` không có quyền
SELECT `votes`.

`receipt = SHA-256(bytes của sig_cast)` dưới dạng hex. `voter_status` lưu chữ ký
`sig_cast` và digest, không lưu `vote_id`. Biên nhận chứng minh server đã nhận chữ ký
cast theo luồng demo; nó chưa chứng minh lá phiếu được đếm đúng theo nghĩa kiểm chứng
đầu cuối.

## Đăng nhập và kiểm phiếu

Mật khẩu cử tri dùng PBKDF2-HMAC-SHA256 với salt riêng; `password_hash` lưu phiên bản,
số vòng lặp và digest. Mã kích hoạt ngẫu nhiên được lưu bằng SHA-256 hash và xóa khi
kích hoạt. JWT HS256 chứa `sub`, `role`, `iat`, `exp`; route yêu cầu đúng role.
Sau giờ kết thúc, `tally_user` đọc ứng viên và phiếu, KMS giải mã envelope trong RAM,
đếm `ballot.candidate_id` và API chỉ trả `results` cùng `total_votes`.

Đã có test cho mã hóa/chữ ký, replay, thời gian, bỏ phiếu đồng thời, rollback và
quyền DB; kết quả chạy hiện tại được ghi tại [ROADMAP.md](../ROADMAP.md).
