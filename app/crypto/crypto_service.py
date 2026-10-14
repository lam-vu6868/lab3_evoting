"""
FILE: app/crypto/crypto_service.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Mã hóa/giải mã envelope lá phiếu, không biết HTTP hay danh tính tài khoản.
PHỤ THUỘC: app/crypto/kms.py; cryptography.hazmat.primitives.ciphers.aead.AESGCM.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. encrypt_vote(plaintext: bytes, kms) trả dict ciphertext, wrapped_dek, iv, tag đều là bytes.
2. Sinh DEK 32 byte và IV 12 byte bằng nguồn ngẫu nhiên mật mã.
3. AESGCM(DEK).encrypt(iv, plaintext, None) trả ciphertext nối tag; tách 16 byte cuối làm tag.
4. Gọi kms.wrap_dek(DEK); trả bốn trường cho voting_service, không trả DEK.
5. decrypt_vote(encrypted, kms): unwrap DEK, nối ciphertext + tag, gọi decrypt cùng IV/AAD.
6. Sai tag/độ dài/khóa phải báo lỗi; không trả plaintext một phần hoặc lờ lỗi.
7. Không ghi khóa/plaintext ra log hoặc DB. Giảm thời gian giữ tham chiếu; del trong Python
   không bảo đảm xóa sạch bytes khỏi bộ nhớ.

TỰ KIỂM TRA:
Round-trip bằng nhau; hai lần mã hóa cùng nội dung khác nhau; sửa ciphertext/IV/tag/wrapped_dek bị phát hiện.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
