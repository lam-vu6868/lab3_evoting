"""
FILE: app/crypto/signature_service.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Chuẩn hóa thông điệp và xác minh chữ ký cử tri; backend không giữ private key cử tri.
PHỤ THUỘC: cryptography; giao ước với static/js/crypto.js; không phụ thuộc DB.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo canonical_bytes(payload): JSON khóa sắp xếp tăng dần, không khoảng trắng, UTF-8.
   Payload phẳng, chỉ trường đã quy định; ts là số nguyên an toàn cho JavaScript.
2. build_ballot(candidate_id, nonce, ts) và build_cast(election_id, voter_id, nonce, ts).
3. load_voter_public_key(pem): nhận SPKI PEM PUBLIC KEY; kiểm tra RSA 2048.
4. verify_signature(public_key, payload, signature_bytes): RSA-PSS, SHA-256,
   MGF1 SHA-256, salt_length=32. JS phải dùng đúng saltLength=32.
5. Chữ ký truyền HTTP bằng Base64 chuẩn, decode chặt chẽ trước verify.
6. Tách hàm thuần khỏi HTTPException; trả kết quả/lỗi để main chuyển thành HTTP.
7. Sinh key/sign trong Python chỉ dùng cho test; khóa cử tri thật sinh trong browser.

TỰ KIỂM TRA:
JS và Python tạo cùng byte JSON; chữ ký JS được Python chấp nhận; đổi candidate/nonce/ts hoặc public key thì verify thất bại.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
