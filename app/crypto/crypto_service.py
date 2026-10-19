"""
FILE: app/crypto/crypto_service.py
TRẠNG THÁI: Đã triển khai mã hóa/giải mã AES-GCM; chưa tích hợp luồng bỏ phiếu.
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
Chạy python -m unittest tests.test_crypto -v với khóa tạm.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

# Dùng để sinh số ngẫu nhiên từ hệ điều hành qua os.urandom().
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.crypto.kms import KMS


# luồng nhận phiếu và kiểm tra mã hóa 
def encrypt_vote(plaintext: bytes, kms: KMS) -> dict[str, bytes]:
    """Trả bốn trường bytes để lưu vào bảng votes; không trả khóa AES gốc."""
    if not isinstance(plaintext, bytes):
        raise TypeError("plaintext phải là bytes")

    # AESGCM sinh khóa 256 bit mới; os.urandom sinh IV 12 byte mới cho mỗi phiếu.
    dek = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    # cryptography trả ciphertext nối với tag xác thực 16 byte ở cuối.
    ciphertext_with_tag = AESGCM(dek).encrypt(iv, plaintext, None)
    return {
        "ciphertext": ciphertext_with_tag[:-16],
        "wrapped_dek": kms.wrap_dek(dek),
        "iv": iv,
        "tag": ciphertext_with_tag[-16:],
    }


# kiểm phiếu 
def decrypt_vote(encrypted: dict[str, bytes], kms: KMS) -> bytes:
    """Chỉ trả plaintext khi khóa và tag xác thực đều hợp lệ."""
    for field in ("ciphertext", "wrapped_dek", "iv", "tag"):
        if not isinstance(encrypted[field], bytes):
            raise TypeError(f"{field} phải là bytes")
    if len(encrypted["iv"]) != 12 or len(encrypted["tag"]) != 16:
        raise ValueError("IV phải 12 byte và tag phải 16 byte")

    dek = kms.unwrap_dek(encrypted["wrapped_dek"])
    # AESGCM yêu cầu ghép tag lại; dữ liệu bị sửa sẽ phát sinh InvalidTag.
    return AESGCM(dek).decrypt(
        encrypted["iv"], encrypted["ciphertext"] + encrypted["tag"], None
    )
