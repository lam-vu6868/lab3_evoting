# Bài thuyết trình: Hệ thống bầu cử điện tử

**Cách dùng:** Mở file ở chế độ xem trước Markdown có hỗ trợ Mermaid để thấy các ô và mũi tên của `sequenceDiagram`, rồi đọc lần lượt các đoạn **Em trình bày**. Không cần đọc từng ký hiệu trên sơ đồ. Toàn bài theo một ví dụ giả: cử tri `SV001` chọn ứng viên B (`candidate_id = 2`). Không đưa mã kích hoạt, mật khẩu, JWT hay khóa riêng thật lên màn hình lớp.

## 1. Mục tiêu của đề tài

**Sơ đồ hành trình:**

```mermaid
sequenceDiagram
    participant CT as Cử tri SV001
    participant HT as Hệ thống
    participant DB as Database
    participant AD as Admin
    CT->>HT: Kích hoạt và đăng nhập
    CT->>HT: Chọn B và gửi phiếu
    HT->>DB: Kiểm tra và lưu phiếu đã mã hóa
    AD->>HT: Yêu cầu kết quả sau giờ kết thúc
    HT->>DB: Đọc phiếu để đếm
    HT-->>AD: Trả tổng phiếu theo ứng viên
```

**Em trình bày:** “Đây là sơ đồ tổng quan của hệ thống; em xin đọc từ trên xuống. Đầu tiên, cử tri SV001 kích hoạt tài khoản và đăng nhập. Tiếp theo, SV001 chọn ứng viên B rồi gửi phiếu. Hệ thống kiểm tra và lưu phiếu dưới dạng đã mã hóa trong database. Sau khi cuộc bầu cử kết thúc, admin yêu cầu xem kết quả; hệ thống đọc các phiếu để đếm và chỉ trả tổng theo ứng viên. Ở các sơ đồ sau, em sẽ giải thích từng bước này diễn ra như thế nào.”

## 2. Công nghệ và nhiệm vụ của từng phần

| Phần                    | Công nghệ                                 | Công việc                                                   |
| ----------------------- | ----------------------------------------- | ----------------------------------------------------------- |
| Giao diện               | HTML, CSS, JavaScript trong `static/`     | Bốn trang: kích hoạt, đăng nhập, bỏ phiếu, quản trị.        |
| Mật mã trên trình duyệt | Web Crypto API                            | Tạo cặp khóa RSA-PSS của cử tri và ký trước khi gửi phiếu.  |
| Backend                 | Python, FastAPI,                          | Nhận API, kiểm JSON, xác thực và thực hiện nghiệp vụ.       |
| Database                | PostgreSQL, SQLAlchemy                    | Lưu dữ liệu bầu cử; ngăn một cử tri gửi thành công hai phiếu cùng lúc. |
| Xác thực                | PBKDF2-HMAC-SHA256 với salt, JWT ký HS256 | Lưu hash mật khẩu, cấp mã đăng nhập có hạn và kiểm role.    |
| Phiếu và khóa           | RSA-PSS, AES-256-GCM, RSA-OAEP            | Ký phiếu, mã hóa phiếu và bọc khóa AES.                     |

**Sơ đồ các thành phần trao đổi:**

```mermaid
sequenceDiagram
    participant CT as Trình duyệt cử tri
    participant AD as Trình duyệt admin
    participant API as FastAPI
    participant DB as PostgreSQL
    participant KMS as KMS mô phỏng
    CT->>API: Gọi activate, login, candidates, vote
    API->>DB: app_user đọc và ghi theo quyền
    API->>KMS: Bọc khóa AES của phiếu
    AD->>API: Gọi admin/login rồi results
    API->>DB: tally_user đọc votes và candidates
    API->>KMS: Mở khóa AES để kiểm phiếu
    API-->>AD: Trả tổng kết quả
    Note over API,KMS: KMS là module trong backend, không phải dịch vụ riêng
```

**Em trình bày:** “Frontend có bốn trang, backend FastAPI có sáu API. Docker hiện chỉ chạy PostgreSQL; backend chạy local. Ví dụ, nếu SV001 bấm gửi phiếu hai lần rất nhanh, yêu cầu thứ hai phải chờ; khi được xử lý, nó thấy SV001 đã bầu và bị từ chối. Nếu quá trình ghi phiếu gặp lỗi, hệ thống hủy cả mã dùng một lần, phiếu và trạng thái đã bầu, nên không bị ghi dở. Database có ba role: `app_user` dùng cho luồng cử tri và ghi phiếu, `tally_user` dùng đọc phiếu để kiểm, còn `admin_app` theo quyền SQL chỉ đọc ứng viên. Tài khoản admin trên giao diện được so với cấu hình backend, không phải role `admin_app` và không có bảng admin.”

## 3. Chuẩn bị cử tri và kích hoạt

**Sơ đồ kích hoạt SV001:**

```mermaid
sequenceDiagram
    participant NV as Người vận hành
    participant WEB as Trình duyệt SV001
    participant API as POST /activate
    participant DB as PostgreSQL
    NV->>DB: Seed SV001 với hash mã kích hoạt
    Note over DB: voters.activated = false
    WEB->>WEB: SV001 nhập mã, mật khẩu và bấm nút
    WEB->>WEB: Tạo cặp RSA-PSS, lưu hai khóa trong localStorage
    WEB->>API: Gửi voter_id, mã, mật khẩu, CHỈ public key
    API->>DB: Khóa dòng voters của SV001
    DB-->>API: Trả trạng thái và hash mã kích hoạt
    alt Mã đúng, chưa kích hoạt, public key hợp lệ
        API->>DB: Lưu password_hash, salt, public_key
        API->>DB: Tạo voter_status.has_voted = false
        DB-->>API: Commit
        API-->>WEB: success = true
        WEB->>WEB: Cử tri có thể bấm tải file private key
    else Thông tin không hợp lệ
        API-->>WEB: Báo lỗi, không ghi public key vào DB
    end
    Note over WEB: Khóa được tạo trước khi server xác nhận mã đúng
```

**Em trình bày:** “Trước hết, script `seed_voters.py` thêm `SV001` vào bảng `voters`. Database chỉ lưu **hash của mã kích hoạt**, không lưu mã nguyên bản. Khi SV001 điền form và bấm nút, trình duyệt tạo hai khóa: private key để cử tri ký về sau, public key để backend kiểm chữ ký. Hai khóa được lưu trong `localStorage`, nhưng request chỉ gửi public key. Backend kiểm mã kích hoạt có thuộc SV001 không, kiểm khóa công khai, khóa dòng cử tri để tránh kích hoạt đồng thời, rồi lưu `password_hash`, `salt`, `public_key`, đặt `activated=true` và thêm dòng `voter_status` với `has_voted=false`. Chỉ sau commit mới báo kích hoạt thành công.”

**Em nhấn mạnh:** “Khóa được tạo **sau khi bấm nút**, nhưng **trước khi server xác nhận mã kích hoạt đúng**. Nếu mã sai, public key không vào database; khóa đã tạo vẫn ở trình duyệt để thử lại. Mật khẩu tối thiểu 8 **ký tự**, không bắt buộc 8 chữ số.”

**Sao lưu khóa:** Sau khi khóa đã nằm trong `localStorage`, cử tri **bấm nút tải** để tạo file sao lưu private key; file không tự tải. Nếu đổi thiết bị, cử tri đăng nhập rồi nhập file sao lưu tại trang bỏ phiếu. Private key cử tri không được gửi lên backend. Salt là giá trị ngẫu nhiên riêng cho mỗi tài khoản: hai người dùng cùng mật khẩu vẫn có hash khác nhau.

**Code đối chiếu:** [seed_voters.py](../app/database/seed_voters.py), [activate.js](../static/js/activate.js), [crypto.js](../static/js/crypto.js), [activate.py](../app/auth/activate.py).

## 4. Đăng nhập và xem ứng viên

**Sơ đồ đăng nhập:**

```mermaid
sequenceDiagram
    participant WEB as Trình duyệt SV001
    participant API as FastAPI
    participant DB as PostgreSQL
    WEB->>API: POST /login với voter_id và mật khẩu
    API->>DB: Đọc voters của SV001
    DB-->>API: activated, password_hash, salt
    API->>API: Kiểm mật khẩu và tạo JWT role voter
    API-->>WEB: JWT và election_id
    WEB->>WEB: Lưu trong sessionStorage
    WEB->>API: GET /candidates
    API->>DB: Đọc bảng candidates
    DB-->>API: Danh sách ứng viên A, B, C
    API-->>WEB: Hiển thị lựa chọn trên vote.html
```

**Em trình bày:** “Đăng nhập chỉ **đọc** bảng `voters`. Backend kiểm tài khoản đã kích hoạt và mật khẩu khớp hash. Nếu đúng, backend cấp JWT: một mã dùng để chứng minh các request sau thuộc phiên đăng nhập của SV001. JWT được ký HS256 để phát hiện nội dung bị sửa, nhưng **không được mã hóa**, nên không chứa mật khẩu hoặc private key. Token mặc định hết hạn sau 60 phút và được lưu trong `sessionStorage`. Trang bỏ phiếu gọi `/candidates` để đọc danh sách ứng viên. Đăng nhập hay xem ứng viên đều chưa ghi phiếu.”

**Nếu thầy hỏi về JWT bị lộ:** “Người có JWT còn hạn có thể gọi API như phiên đã đăng nhập. Nhưng chỉ JWT chưa đủ bỏ phiếu hợp lệ; phải có private key cử tri để tạo chữ ký. Đăng xuất xóa JWT trên trình duyệt hiện tại, không thu hồi bản token đã bị lấy cắp trước khi hết hạn.”

**Code:** [login.js](../static/js/login.js), [login.py](../app/auth/login.py), [candidates.py](../app/api/candidates.py).

## 5. Cử tri ký hai nội dung trước khi gửi

**Sơ đồ ký phiếu chọn B:**

```mermaid
sequenceDiagram
    participant CT as Cử tri SV001
    participant WEB as vote.js và crypto.js
    participant API as POST /vote
    participant DB as PostgreSQL
    CT->>WEB: Chọn B rồi bấm Ký và gửi phiếu
    WEB->>WEB: Nạp private key SV001 đã có
    WEB->>WEB: Tạo nonce mới và lấy ts hiện tại
    Note over WEB: Lúc bỏ phiếu không tạo cặp RSA mới
    WEB->>WEB: Tạo ballot với candidate_id = 2, nonce, ts
    WEB->>WEB: Tạo cast với election_id, SV001, cùng nonce, ts
    WEB->>WEB: RSA-PSS ký ballot thành sig_ballot
    WEB->>WEB: RSA-PSS ký cast thành sig_cast
    WEB->>API: Gửi ballot, hai chữ ký và JWT
    API->>DB: Lấy public key của SV001 trong voters
    DB-->>API: Public key cử tri
    API->>API: Dựng lại cast và kiểm cả hai chữ ký
```

**Em trình bày:** “Khi SV001 chọn B và bấm gửi, browser tạo `ballot`, nghĩa là nội dung lựa chọn ứng viên 2. Browser còn tạo `cast`, nghĩa là SV001 xác nhận **hành động gửi phiếu cho cuộc bầu cử này**. `nonce` là mã ngẫu nhiên chỉ dùng một lần; `ts` là thời gian Unix tính theo giây. Hai nội dung dùng cùng nonce và ts. Browser dùng private key của SV001 và RSA-PSS ký riêng từng nội dung. Backend dùng public key đã lưu để kiểm. Nếu ai sửa lựa chọn B thành A, chữ ký ballot không còn khớp. Nếu ai chỉ lấy được JWT mà không có private key, họ không tạo được hai chữ ký hợp lệ.”

**Phân biệt:** `ballot` nói **chọn ai**; `cast` nói **ai thực hiện lần bỏ phiếu này, cho cuộc bầu cử nào**. Object `cast` không được gửi hoặc lưu nguyên dạng: backend dựng lại nó để kiểm `sig_cast`. `sig_ballot` đi cùng phiếu đã mã hóa; `sig_cast` được lưu trong `voter_status`.

**Code:** [vote.js](../static/js/vote.js), [signature_service.py](../app/crypto/signature_service.py), [voting_service.py](../app/voting/voting_service.py).

## 6. Backend kiểm tra rồi mã hóa phiếu

**Sơ đồ kiểm tra trước khi ghi:**

```mermaid
sequenceDiagram
    participant WEB as Trình duyệt SV001
    participant API as FastAPI /vote
    participant DB as PostgreSQL
    WEB->>API: Gửi phiếu và JWT
    API->>API: Kiểm role, giờ bầu, ts
    API->>DB: Đọc SV001 và ứng viên B
    DB-->>API: Tài khoản và ứng viên
    API->>API: Kiểm hai chữ ký RSA-PSS
    API->>DB: SELECT voter_status FOR UPDATE
    DB-->>API: has_voted = false?
    alt SV001 chưa bầu
        API->>DB: INSERT nonce từ browser vào used_nonces
        alt Nonce chưa từng dùng
            DB-->>API: Cho phép tiếp tục mã hóa và ghi phiếu
        else Nonce trùng
            DB-->>API: Báo lỗi, transaction rollback
        end
    else SV001 đã bầu
        API-->>WEB: Từ chối bầu lần hai
    end
```

**Em trình bày:** “Backend kiểm thời gian, cử tri, ứng viên và cả hai chữ ký. Nó khóa dòng `voter_status` của SV001 bằng `FOR UPDATE` và kiểm `has_voted=false`, vì hai request gửi cùng lúc không được cùng thành công. Nonce đã dùng bị database từ chối. Nonce chặn **gửi lại cùng yêu cầu cũ**; `has_voted` chặn **SV001 dùng nonce mới để bầu lần hai**.”

**Sơ đồ mã hóa và bọc khóa — phần cần chỉ chậm theo từng mũi tên:**

```mermaid
sequenceDiagram
    participant API as voting_service.py
    participant CR as crypto_service.py
    participant KMS as KMS mô phỏng
    participant DB as Bảng votes
    API->>API: Gói ballot chọn B và sig_ballot thành plaintext
    Note over API: Backend thấy lựa chọn B trước khi mã hóa
    API->>CR: encrypt_vote(plaintext, kms)
    CR->>CR: Tạo DEK AES mới 32 byte và IV 12 byte
    CR->>CR: AES-256-GCM tạo ciphertext và tag 16 byte
    CR->>KMS: wrap_dek(DEK) bằng public key RSA-OAEP
    KMS-->>CR: wrapped_dek
    CR-->>API: ciphertext, wrapped_dek, iv, tag
    API->>DB: INSERT vote_id và bốn trường mã hóa
    Note over DB: Không lưu DEK gốc hoặc phiếu rõ
```

**Sơ đồ KMS mô phỏng có khóa từ đâu:**

```mermaid
sequenceDiagram
    participant API as Backend khởi động
    participant KMS as KMS mô phỏng
    participant FS as Thư mục khóa KMS
    API->>KMS: ensure_keys()
    KMS->>FS: Kiểm tra cặp RSA của hệ thống
    alt Chưa có cả hai file khóa
        KMS->>FS: Tạo private_key.pem và public_key.pem
    else Private key đã có
        FS-->>KMS: Nạp private key cũ, phục hồi public key nếu cần
    else Còn public key nhưng mất private key
        KMS-->>API: Báo lỗi, không tạo khóa thay thế
    end
    Note over KMS,FS: Khóa KMS được dùng lại qua các lần khởi động
    API->>KMS: Khi bỏ phiếu, dùng public key bọc DEK
    API->>KMS: Khi kiểm phiếu, dùng private key mở DEK
```

**Em nói rõ:** “KMS ở bài này là module quản lý khóa mô phỏng trong backend, lưu cặp RSA trong thư mục cấu hình. Nó không phải dịch vụ KMS độc lập và **không tạo cặp khóa mới cho mỗi phiếu**. Mỗi phiếu chỉ có **DEK AES mới**. Nếu làm mất private key KMS cũ thì không mở được DEK của các phiếu cũ.”

**Em trình bày:** “Backend gói `ballot` và `sig_ballot` thành dữ liệu phiếu. Nó tạo một **khóa AES mới 32 byte cho riêng phiếu này**, gọi là DEK, và một IV ngẫu nhiên 12 byte. AES-256-GCM dùng DEK và IV biến phiếu rõ thành `ciphertext`, tức dữ liệu không đọc trực tiếp được. Thuật toán còn tạo `tag` 16 byte để khi giải mã có thể phát hiện dữ liệu bị sửa hoặc dùng sai khóa. Nhưng nếu lưu DEK gốc cạnh phiếu thì người đọc database có thể mở phiếu. Vì vậy public key của KMS mô phỏng dùng RSA-OAEP bọc DEK thành `wrapped_dek`. Database chỉ lưu khóa đã bọc.”

| Cột trong `votes` | Có tác dụng gì?                                                              |
| ----------------- | ---------------------------------------------------------------------------- |
| `vote_id`         | ID ngẫu nhiên của dòng phiếu.                                                |
| `ciphertext`      | Phiếu đã AES mã hóa; không đọc trực tiếp được lựa chọn B.                    |
| `wrapped_dek`     | Khóa AES đã được public key KMS bọc bằng RSA-OAEP.                           |
| `iv`              | 12 byte dùng cho đúng lần mã hóa này; cần lại để giải mã, không phải bí mật. |
| `tag`             | 16 byte dùng kiểm dữ liệu hoặc khóa có sai/bị sửa không.                     |

**Em giải thích ba thuật toán:** “**RSA-PSS** dùng cặp khóa của **cử tri** để ký và kiểm chữ ký. **AES-256-GCM** dùng DEK để mã hóa nội dung phiếu. **RSA-OAEP** dùng cặp khóa của **KMS** để bảo vệ DEK. Hai cặp RSA khác nhau: private key cử tri ở trình duyệt, private key KMS ở backend. Backend **thấy lựa chọn B trước khi mã hóa**; đây là giới hạn của hệ thống hiện tại.”

**Code:** [crypto_service.py](../app/crypto/crypto_service.py), [kms.py](../app/crypto/kms.py), [voting_service.py](../app/voting/voting_service.py).

## 7. Database ghi phiếu trong một transaction

**Sơ đồ ghi và trả biên nhận:**

```mermaid
sequenceDiagram
    participant WEB as Trình duyệt SV001
    participant API as POST /vote
    participant DB as PostgreSQL
    API->>DB: BEGIN trước các bước kiểm tra và ghi phiếu
    API->>DB: Đọc cử tri, ứng viên và khóa dòng trạng thái
    API->>DB: INSERT used_nonces với nonce
    API->>API: Mã hóa phiếu và bọc DEK
    API->>DB: INSERT votes với bốn trường mã hóa
    API->>DB: UPDATE voter_status với has_voted, sig_cast, receipt_hash
    alt Mọi bước thành công
        DB-->>API: COMMIT
        API-->>WEB: success và receipt dạng hex
    else Một bước lỗi
        DB-->>API: ROLLBACK mọi thay đổi
        API-->>WEB: Trả lỗi, không báo thành công
    end
```

**Em trình bày:** “Ba thay đổi này phải thành công cùng nhau. `used_nonces` chặn dùng lại nonce. `votes` chứa phiếu mã hóa và **không có cột `voter_id` hoặc `candidate_id` riêng**. `voter_status` ghi SV001 đã bỏ phiếu và lưu chữ ký `sig_cast`. Backend tính `receipt_hash` là SHA-256 của bytes chữ ký `sig_cast`, lưu hash đó rồi trả bản hex làm biên nhận **sau commit**. `receipt_hash` có thể tính lại từ `sig_cast`; hệ thống hiện chưa có trang tra cứu biên nhận và nó chưa chứng minh phiếu đã được tính vào kết quả cuối cùng.”

**Sơ đồ dữ liệu được đọc hoặc ghi ở năm bảng:**

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant V as voters
    participant C as candidates
    participant S as voter_status
    participant N as used_nonces
    participant P as votes
    API->>V: Đọc SV001, public key và trạng thái kích hoạt
    API->>C: Kiểm ứng viên B tồn tại
    API->>S: Khóa dòng SV001 và kiểm has_voted
    API->>N: Ghi nonce chưa dùng
    API->>P: Ghi ciphertext, wrapped_dek, iv, tag
    API->>S: Ghi has_voted, sig_cast, receipt_hash
    Note over P: votes không có cột voter_id
```

**Code:** [vote.py](../app/voting/vote.py), [voting_service.py](../app/voting/voting_service.py), [init.sql](../db/init.sql).

## 8. Hết giờ bầu cử: admin kiểm phiếu

**Sơ đồ giải mã — đi ngược sơ đồ mã hóa:**

```mermaid
sequenceDiagram
    participant AD as Admin
    participant API as GET /results
    participant DB as PostgreSQL tally_user
    participant KMS as KMS mô phỏng
    participant CR as AES-256-GCM
    AD->>API: Gửi JWT role admin
    alt Chưa đến giờ kết thúc
        API-->>AD: Từ chối xem kết quả
    else Đã hết giờ bầu cử
        API->>DB: Đọc candidates và votes
        DB-->>API: Danh sách phiếu mã hóa
        loop Với mỗi phiếu
            API->>KMS: Dùng private key mở wrapped_dek
            KMS-->>API: DEK gốc
            API->>CR: Giải mã ciphertext với DEK, iv, tag
            CR-->>API: ballot và sig_ballot
            API->>API: candidate_id = 2 thì cộng 1 cho B
        end
        API-->>AD: Chỉ trả tổng theo ứng viên và total_votes
    end
```

**Em trình bày:** “Admin đăng nhập bằng `/admin/login`. Trước giờ kết thúc, `/results` từ chối và chưa đọc phiếu. Sau giờ kết thúc, backend dùng tài khoản database `tally_user` đọc `votes` và `candidates`. Với từng phiếu, private key KMS mở `wrapped_dek` để lấy lại DEK. AES-GCM dùng DEK cùng IV, ciphertext và tag để giải mã. Nếu tag hoặc dữ liệu sai, lượt kiểm phiếu báo lỗi chứ không trả một tổng sai. Với phiếu ví dụ, backend đọc `candidate_id=2` và cộng một cho B. API chỉ trả **tổng phiếu**, không trả từng phiếu đã giải mã cho admin.”

**Giới hạn riêng tư:** “Tách `votes` và `voter_status` tránh liên kết trực tiếp tên cử tri với phiếu, nhưng **không đảm bảo ẩn danh tuyệt đối**. Backend đã thấy B trước khi mã hóa và KMS mô phỏng nằm cùng backend.”

**Code:** [admin.py](../app/auth/admin.py), [results.py](../app/voting/results.py), [tally.py](../app/voting/tally.py).

## 9. Kiểm tra và giới hạn của hệ thống

**Em trình bày:** “Theo các checkpoint trong [ROADMAP.md](../ROADMAP.md), dự án đã thử với **dữ liệu giả và database thử nghiệm riêng**: mã kích hoạt sai; hai yêu cầu kích hoạt đồng thời; mật khẩu và JWT sai; chữ ký sai; nonce lặp; hai yêu cầu bỏ phiếu đồng thời chỉ một thành công; lỗi giữa transaction phải rollback; chặn xem kết quả trước giờ; và một luồng từ kích hoạt đến kết quả trong trình duyệt. Đây là kết quả của những trường hợp đã thử, không phải chứng nhận an toàn để bầu cử thật.”

**Em nói rõ điều chưa làm:** “Private key cử tri trong browser và file sao lưu có thể lộ nếu thiết bị hoặc trang bị tấn công. Nhập khóa trên thiết bị mới chưa được kiểm chứng đầy đủ. Backend thấy lựa chọn trước mã hóa; KMS chưa tách khỏi backend; biên nhận chưa cho người dùng tự kiểm tra phiếu đã được tính đúng; chưa kiểm tải lớn và chưa có kiểm toán bảo mật độc lập.”

## 10. Kết luận để đọc trước lớp

**Em trình bày:** “Tóm lại, cử tri dùng **RSA-PSS** để ký, backend dùng **AES-256-GCM** để mã hóa phiếu và **RSA-OAEP của KMS** để bọc khóa AES. PostgreSQL dùng transaction và khóa dòng để phiếu hoặc được ghi đủ hoặc không ghi gì, đồng thời chặn bỏ phiếu hai lần. Sau khi kết thúc, backend giải mã trong RAM và chỉ trả tổng theo ứng viên. Mỗi lớp có một nhiệm vụ: chữ ký xác nhận nội dung, mã hóa bảo vệ phiếu lưu trữ, database lưu trạng thái và quyền. Hệ thống đáp ứng mục tiêu học tập, **chưa phải hệ thống bầu cử dùng thật**.”

## Phần dự phòng: trả lời câu hỏi thường gặp

- **Public key có kiểm SV001 đã bầu chưa?** Không. Public key kiểm chữ ký; `voter_status.has_voted` mới trả lời đã bầu chưa.
- **Nonce khác `has_voted` ở đâu?** Nonce chặn dùng lại một request cũ; `has_voted` chặn SV001 bầu lần hai dù dùng nonce mới.
- **JWT HS256 có mã hóa thông tin không?** Không. Nó ký để phát hiện token bị sửa; thông tin trong token có thể đọc được.
- **Ai lấy được JWT có bỏ phiếu thay SV001 được không?** JWT cho phép gọi API như phiên đăng nhập còn hạn; muốn ký phiếu hợp lệ còn cần private key cử tri.
- **`sig_cast` và `receipt_hash` dùng làm gì?** Một cột lưu chữ ký hành động bỏ phiếu; cột kia lưu hash chữ ký làm biên nhận. Hai cột không được dùng để đếm phiếu.
- **IV và tag dùng làm gì?** IV là giá trị của lần mã hóa AES; tag giúp phát hiện dữ liệu bị sửa hoặc khóa sai khi giải mã.
- **DEK gốc có lưu trong DB không?** Không. Chỉ có `wrapped_dek`, tức DEK đã được public key KMS bọc.
- **KMS là gì?** Trong bài này là module quản lý khóa mô phỏng của backend. `tally_user` là role DB đọc phiếu để kiểm.
- **Vì sao không nói ẩn danh tuyệt đối?** Backend thấy lựa chọn trước mã hóa; dữ liệu sau giải mã và thông tin khác có thể tạo liên kết gián tiếp.

**Tài liệu tra thêm:** [Sodoluong/README.md](../Sodoluong/README.md), [STRUCTURE.md](STRUCTURE.md), [technical.md](technical.md), [risk-analysis.md](risk-analysis.md). Khi trình bày trực tiếp trước lớp, chỉ dùng dữ liệu giả; kiểm tra giờ bầu cử và DB thử nghiệm trước, không xóa dữ liệu hoặc tạo lại khóa KMS đang dùng.
