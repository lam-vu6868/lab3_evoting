<!--
FILE: docs/Luong_du_lieu_he_thong_bau_cu.md
MỤC ĐÍCH: Nguồn văn bản 10 phần để đọc và sinh Word cho NotebookLM.
CÁCH DÙNG / VIỆC CẦN LÀM:
Sửa nội dung tại đây; chạy python docs/build_flow_docx.py để cập nhật .docx.
Đây là tài liệu thiết kế, không phải bằng chứng backend đã triển khai.
Quy ước triển khai mới nhất xem STRUCTURE.md và comment module.
-->

# LUỒNG DỮ LIỆU HỆ THỐNG BẦU CỬ ĐIỆN TỬ

Tài liệu giải thích theo ví dụ, dùng để đọc và làm nguồn cho NotebookLM.

**Đăng nhập chỉ đọc thông tin tài khoản và cấp JWT; đến lúc bỏ phiếu mới ghi phiếu vào database.** Mình đi theo một ví dụ xuyên suốt để bạn thấy rõ từng dữ liệu chạy đi đâu:

Ví dụ: Cử tri SV001 — Nguyễn An, kích hoạt tài khoản, đăng nhập rồi bầu ứng viên B có mã 2.

Luồng dưới đây bám theo db/init.sql và ROADMAP.md trong dự án D:\HeThongBauCu. Đây là thiết kế dự kiến; các file Python hiện chưa triển khai xử lý. Những giá trị như HASH_PASSWORD, KEY_AES_1 bên dưới chỉ là ký hiệu minh họa.

## 1. Trước khi bạn đăng nhập: hệ thống đã chuẩn bị gì?

Khi khởi tạo database, SQL tạo 5 bảng và thêm 3 ứng viên vào candidates:

| candidate_id | name | party |
| --- | --- | --- |
| 1 | Nguyễn Văn A | Đảng X |
| 2 | Trần Thị B | Đảng Y |
| 3 | Lê Văn C | Đảng Z |

Script app/database/seed_voters.py dự kiến tạo danh sách cử tri và mã kích hoạt. Với SV001, dòng trong voters ban đầu sẽ như sau:

| Cột | Giá trị ban đầu |
| --- | --- |
| voter_id | SV001 |
| full_name | Nguyễn An |
| activation_hash | Hash của mã kích hoạt |
| activated | false |
| password_hash | NULL |
| salt | NULL |
| public_key | NULL |
| created_at | Thời điểm tạo dòng, DB tự điền |

Mã kích hoạt nguyên bản được cung cấp cho cử tri; database giữ hash để kiểm tra.

Cũng ở giai đoạn khởi động backend, KMS dự kiến sinh cặp khóa RSA nếu chưa có, lưu ở thư mục KMS_KEY_DIR (dự kiến ./kms_keys trên máy local). Hiện Docker chỉ chạy PostgreSQL; khóa KMS không nằm trong 5 bảng này.

## 2. Bạn kích hoạt tài khoản: tạo khóa cử tri và lưu mật khẩu

Bạn nhập:

```text
Mã cử tri:    SV001
Mã kích hoạt: mã đã được cấp
Mật khẩu:     mật khẩu bạn tự chọn
```

Trình duyệt tạo cặp khóa RSA của riêng SV001:

```text
PRIVATE KEY SV001 → giữ tại trình duyệt
PUBLIC KEY SV001  → gửi lên backend
```

Sơ đồ luồng kích hoạt, đọc từ trên xuống:

```text
[Cử tri] Nhập mã cử tri, mã kích hoạt, mật khẩu
    ↓
[Trình duyệt] Sinh cặp khóa RSA, giữ private key
    ↓ POST /activate + thông tin nhập + public key
[Backend] Đọc voters theo voter_id
    ↓
[Database] Trả activation_hash và activated
    ↓
[Backend] Kiểm tra mã kích hoạt, băm mật khẩu
    ↓
[Database] UPDATE voters và INSERT voter_status
    ↓
[Trình duyệt] Nhận thông báo kích hoạt thành công
```

Backend cập nhật dòng SV001 trong voters:

| Cột | Trước | Sau |
| --- | --- | --- |
| activation_hash | Hash mã kích hoạt | NULL — vô hiệu hóa mã |
| activated | false | true |
| password_hash | NULL | HASH_PASSWORD |
| salt | NULL | Tùy thuật toán băm |
| public_key | NULL | Public key SV001 dạng PEM |

voter_id, full_name, created_at vẫn giữ giá trị đã có.

Về salt: nếu dùng thuật toán lưu salt bên trong chuỗi hash như roadmap đề xuất thì cột riêng này có thể để NULL; phần này chưa được triển khai.

Đồng thời, backend thêm dòng vào voter_status:

| voter_id | has_voted | sig_cast | receipt_hash | voted_at |
| --- | --- | --- | --- | --- |
| SV001 | false | NULL | NULL | NULL |

Sau kích hoạt: database biết bạn là ai, có thông tin kiểm tra mật khẩu và chữ ký, nhưng bạn chưa bỏ phiếu.

## 3. Bạn đăng nhập: đọc cột nào, tạo mã gì?

Trình duyệt gửi:

```text
POST /login
voter_id: SV001
password: mật khẩu bạn nhập
```

Backend tìm dòng voters.voter_id = "SV001" và đọc:

| Cột | Để làm gì? |
| --- | --- |
| voter_id | Xác định tài khoản |
| activated | Kiểm tra tài khoản đã kích hoạt |
| password_hash | Kiểm tra mật khẩu |
| salt | Dùng khi thuật toán băm cần cột salt riêng |

Nếu đúng, backend tạo JWT bằng cấu hình JWT_SECRET, trả về trình duyệt.

Thông tin JWT về mặt ý nghĩa:

```text
Người đăng nhập: SV001
Thời hạn: đến thời điểm X
```

Tên trường và thời hạn cụ thể chưa được code chốt.

Sơ đồ luồng đăng nhập:

```text
[Trình duyệt] POST /login: SV001 + mật khẩu
    ↓
[Backend] SELECT thông tin SV001 từ voters
    ↓
[Database] Trả trạng thái kích hoạt và hash mật khẩu
    ↓
[Backend] Kiểm tra mật khẩu → tạo JWT có thời hạn
    ↓
[Trình duyệt] Nhận access_token = JWT
    ↓
[Trình duyệt] Giữ JWT để gửi trong các yêu cầu tiếp theo
```

Đăng nhập thành công không thêm phiếu, không đổi has_voted, không lưu JWT vào bảng nào trong thiết kế này.

Private key cử tri cũng không được tạo lại khi đăng nhập; trình duyệt cần dùng khóa đã giữ từ lúc kích hoạt.

## 4. Mở trang bỏ phiếu: đọc danh sách ứng viên

```text
Trình duyệt gọi GET /candidates
    ↓
Backend đọc bảng candidates
    ↓
Trả candidate_id, name, party
    ↓
Giao diện hiển thị các ứng viên
```

Bạn chọn B, trình duyệt giữ:

```text
candidate_id = 2
```

Chỉ chọn trên giao diện chưa ghi gì vào database.

## 5. Bấm “Bỏ phiếu”: trình duyệt tạo những gì?

Trình duyệt tạo:

```text
nonce = N1  ← mã ngẫu nhiên mới cho lần gửi
ts    = T1  ← thời điểm tạo yêu cầu
```

Sau đó dựng hai nội dung:

```text
ballot = {
    candidate_id: 2,
    nonce: N1,
    ts: T1
}

cast = {
    election_id: E1,
    voter_id: SV001,
    nonce: N1,
    ts: T1
}
```

Dùng private key SV001 ký từng nội dung:

```text
Ký ballot → sig_ballot
Ký cast   → sig_cast
```

Trình duyệt gửi:

```text
POST /vote

Header:
    Authorization: Bearer <JWT>

Nội dung:
    ballot
    sig_ballot
    sig_cast
```

Theo roadmap, server có thể dựng lại cast từ mã cuộc bầu cử đang xử lý, danh tính trong JWT và nonce, ts của ballot để kiểm tra chữ ký. Hai phía phải thống nhất chính xác nội dung ký.

Private key SV001 không nằm trong yêu cầu gửi lên.

## 6. Backend kiểm tra trước khi ghi phiếu

| Kiểm tra | Dữ liệu lấy ở đâu? |
| --- | --- |
| Người gửi là SV001? | Xác minh JWT |
| Đang trong thời gian bầu cử? | ELECTION_START, ELECTION_END từ cấu hình |
| Yêu cầu còn mới? | So ballot.ts với thời gian server |
| Ứng viên 2 có tồn tại? | Đọc candidates.candidate_id |
| Chữ ký đúng? | Đọc voters.public_key của SV001, kiểm tra hai chữ ký |
| SV001 đã bầu chưa? | Đọc và khóa dòng voter_status của SV001 |

Nếu không đạt, backend từ chối yêu cầu.

Nếu đạt, backend tiến hành ghi phiếu trong một transaction. Việc khóa dòng và kiểm tra has_voted phải nằm trong transaction ghi phiếu, như mô tả ở phần 7.

## 7. Backend tạo dữ liệu mã hóa và ghi chính xác vào đâu?

Đầu tiên, backend bắt đầu transaction, khóa dòng trạng thái SV001, kiểm tra has_voted = false, rồi thêm nonce.

Ghi vào used_nonces:

| Cột | Giá trị |
| --- | --- |
| nonce | N1 |
| used_at | Thời gian DB nhận lệnh, tự điền |

Nếu N1 đã có, database báo trùng khóa chính và transaction bị hủy.

Tiếp theo, backend chuẩn bị nội dung cần giấu:

```text
envelope = {
    ballot: {
        candidate_id: 2,
        nonce: N1,
        ts: T1
    },
    sig_ballot: chữ ký của SV001 trên ballot
}
```

Backend tạo khóa AES mới 32 byte, IV mới 12 byte, rồi mã hóa:

```text
envelope + KEY_AES_1 + IV_1
                ↓ AES-256-GCM
        CIPHERTEXT_1 + TAG_1
```

Bảo vệ khóa AES:

```text
KEY_AES_1 + PUBLIC KEY KMS
                ↓ RSA-OAEP
          WRAPPED_DEK_1
```

Thêm một dòng vào votes:

| Cột | Giá trị | Từ đâu ra? |
| --- | --- | --- |
| vote_id | UUID ngẫu nhiên | Backend tạo |
| ciphertext | CIPHERTEXT_1 | Kết quả mã hóa envelope |
| wrapped_dek | WRAPPED_DEK_1 | Khóa AES đã bọc bằng RSA |
| iv | IV_1 | Backend sinh ngẫu nhiên |
| tag | TAG_1 | AES-GCM tạo khi mã hóa |

Không lưu khóa AES nguyên dạng. Không lưu candidate_id = 2 ở cột đọc trực tiếp.

Sau đó backend tạo biên nhận:

```text
RECEIPT_1 = SHA-256(sig_cast)
```

Cập nhật dòng SV001 trong voter_status:

| Cột | Trước | Sau |
| --- | --- | --- |
| voter_id | SV001 | SV001 |
| has_voted | false | true |
| sig_cast | NULL | Chữ ký trên nội dung cast |
| receipt_hash | NULL | RECEIPT_1 |
| voted_at | NULL | Thời điểm bỏ phiếu làm tròn theo giờ |

Ví dụ bầu lúc 10:37 thì voted_at dự kiến lưu mốc 10:00 của giờ tương ứng.

Sơ đồ luồng ghi toàn bộ:

```text
Yêu cầu đã qua kiểm tra ban đầu
    ↓
BEGIN transaction
    ↓
Khóa dòng voter_status của SV001 bằng FOR UPDATE
    ↓
Kiểm tra has_voted = false?
    ├─ Không → ROLLBACK và báo lỗi đã bỏ phiếu
    └─ Có
        ↓
INSERT used_nonces: N1
    ├─ Nonce trùng → ROLLBACK và báo lỗi
    └─ Thành công
        ↓
Sinh khóa AES và IV
    ↓
Mã hóa envelope → ciphertext và tag
    ↓
Public key KMS bọc khóa AES → wrapped_dek
    ↓
INSERT votes: UUID, ciphertext, wrapped_dek, iv, tag
    ↓
UPDATE voter_status: đã bầu, chữ ký, biên nhận, thời gian
    ↓
COMMIT
    ↓
Trả thành công và biên nhận cho trình duyệt
```

Nếu bất kỳ thao tác nào thất bại trước khi commit thì hủy mọi thay đổi của transaction đó. Không để tình trạng “đã đánh dấu bầu nhưng chưa có phiếu”.

## 8. Sau một lần bỏ phiếu thành công, database trông như thế nào?

Giả sử đây là phiếu đầu tiên:

```text
voters
└─ SV001, Nguyễn An, hash mật khẩu, public key...
   Không bị cập nhật bởi việc bỏ phiếu.

candidates
└─ 3 ứng viên như cũ.
   Không có cột tổng phiếu được tăng lên.

voter_status
└─ SV001, true, sig_cast, RECEIPT_1, giờ bỏ phiếu.

used_nonces
└─ N1, thời điểm sử dụng.

votes
└─ UUID_1, CIPHERTEXT_1, WRAPPED_DEK_1, IV_1, TAG_1.
```

Chưa có dòng kết quả kiểu “B được 1 phiếu”. Kết quả chỉ được tính khi Tally giải mã và đếm.

## 9. Admin xem kết quả: đọc gì, giải mã gì, có ghi database không?

Admin gửi username/password đến /admin/login. Backend dự kiến kiểm tra với cấu hình ADMIN_USERNAME, ADMIN_PASSWORD, rồi cấp JWT có quyền admin.

Trong schema hiện tại không có bảng tài khoản admin.

Sơ đồ luồng kiểm phiếu:

```text
[Trình duyệt admin] GET /results + JWT admin
    ↓
[Backend] Kiểm tra quyền và cuộc bầu cử đã kết thúc
    ↓
[Tally] Đọc votes và candidates bằng tài khoản DB tally_user
    ↓
[Database] Trả các phiếu mã hóa và danh sách ứng viên
    ↓
LẶP VỚI MỖI PHIẾU:
    1. Tally gửi wrapped_dek cho KMS.
    2. KMS dùng private key KMS mở khóa AES.
    3. KMS trả khóa AES của phiếu cho Tally.
    4. Tally giải mã ciphertext với khóa AES, IV và tag.
    5. Tally đọc candidate_id và tăng bộ đếm.
    ↓
[Tally] Trả tổng phiếu từng ứng viên cho backend
    ↓
[Backend] Trả kết quả cho trình duyệt admin
```

Với phiếu vừa rồi:

```text
votes.wrapped_dek
    ↓ Private key KMS mở
KEY_AES_1
    ↓ kết hợp votes.iv, votes.tag
    ↓ để giải mã votes.ciphertext
envelope
    ↓ đọc ballot.candidate_id
2
    ↓
Bộ đếm ứng viên 2 tăng thêm 1
```

Theo thiết kế, bộ đếm nằm trong RAM khi kiểm phiếu; không có bảng results để lưu kết quả. Các phiếu mã hóa trong votes vẫn giữ nguyên.

Nếu giải mã hoặc kiểm tra tag thất bại thì không được cộng phiếu đó như phiếu hợp lệ; cách báo lỗi cụ thể hiện chưa được triển khai.

## 10. Bảng tra nhanh: mỗi dữ liệu cuối cùng nằm ở đâu?

| Dữ liệu | Nơi lưu hoặc sử dụng |
| --- | --- |
| Mật khẩu nguyên bản | Nhập ở trình duyệt, backend nhận để kiểm tra/băm; không lưu vào DB |
| Hash mật khẩu | voters.password_hash |
| Public key cử tri | voters.public_key |
| Private key cử tri | Phía trình duyệt cử tri |
| JWT | Trả về trình duyệt để gửi kèm yêu cầu; không có cột lưu trong DB |
| Nonce chống gửi lại | used_nonces.nonce; cũng nằm trong ballot đã mã hóa |
| Timestamp của yêu cầu | Trong ballot đã mã hóa, không phải cột riêng của votes |
| Lựa chọn ứng viên | Bên trong votes.ciphertext |
| sig_ballot | Bên trong votes.ciphertext |
| sig_cast | voter_status.sig_cast |
| Khóa AES nguyên dạng | Bộ nhớ lúc mã hóa/giải mã |
| Khóa AES đã bọc | votes.wrapped_dek |
| IV và tag | votes.iv, votes.tag |
| Khóa KMS | Thư mục KMS_KEY_DIR trên máy chạy backend, ngoài các bảng DB |
| Biên nhận | voter_status.receipt_hash và trả cho cử tri |
| Tổng phiếu từng ứng viên | Tally tính trong RAM rồi trả cho admin |
