"""
FILE: tests/test_crypto.py
TRẠNG THÁI: Đã kiểm tra KMS và AES-GCM; chữ ký, password và JWT chưa triển khai.
MỤC ĐÍCH: Test hàm mật mã và xác thực, không cần PostgreSQL.
PHỤ THUỘC: unittest, tempfile; kms, crypto_service, signature_service, auth.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Viết unittest.TestCase; dùng TemporaryDirectory cho KMS, không dùng volume khóa thật.
2. Test AES round-trip, sửa ciphertext/tag/IV/wrapped key; restart KMS dùng cùng khóa.
3. Sinh khóa cử tri tạm trong test, ký RSA-PSS salt 32 rồi verify; đổi candidate/nonce/ts.
4. Có vector JSON/chữ ký cố định xuất từ WebCrypto để kiểm tương thích JS/Python.
5. Test password salt khác nhau, verify đúng/sai; JWT hết hạn/sai role/sửa chữ ký.
6. Guard unittest.main() để chạy python -m unittest tests.test_crypto.

TỰ KIỂM TRA:
Không có khóa thật trong fixture/Git; từng test xác minh hành vi, không chỉ mock mọi hàm để luôn pass.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

import tempfile
import unittest
from pathlib import Path

from cryptography.exceptions import InvalidTag

from app.crypto.crypto_service import decrypt_vote, encrypt_vote
from app.crypto.kms import KMS


class KMSTests(unittest.TestCase):
    """Kiểm tra KMS bằng thư mục tạm, không chạm vào khóa thật của dự án."""

    def test_wrap_then_unwrap_returns_original_dek(self):
        """Khóa AES sau khi bọc và mở phải giống hệt khóa ban đầu."""
        with tempfile.TemporaryDirectory() as key_dir:
            kms = KMS(key_dir)
            kms.ensure_keys()
            dek = b"a" * 32

            wrapped_dek = kms.wrap_dek(dek)

            self.assertNotEqual(wrapped_dek, dek)
            self.assertEqual(kms.unwrap_dek(wrapped_dek), dek)

    def test_new_kms_instance_reuses_existing_private_key(self):
        """Backend khởi động lại vẫn phải mở được khóa AES của phiếu cũ."""
        with tempfile.TemporaryDirectory() as key_dir:
            first_kms = KMS(key_dir)
            first_kms.ensure_keys()
            wrapped_dek = first_kms.wrap_dek(b"b" * 32)

            restarted_kms = KMS(key_dir)
            restarted_kms.ensure_keys()

            self.assertEqual(restarted_kms.unwrap_dek(wrapped_dek), b"b" * 32)

    def test_missing_private_key_is_not_silently_replaced(self):
        """Còn public key mà mất private key phải báo lỗi để bảo vệ phiếu cũ."""
        with tempfile.TemporaryDirectory() as key_dir:
            public_key_path = Path(key_dir) / "public_key.pem"
            public_key_path.write_text("public key cũ", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "private key"):
                KMS(key_dir).ensure_keys()

    def test_wrap_rejects_dek_that_is_not_32_bytes(self):
        """Thiết kế chỉ chấp nhận khóa AES-256, tức đúng 32 byte."""
        with tempfile.TemporaryDirectory() as key_dir:
            kms = KMS(key_dir)
            kms.ensure_keys()

            with self.assertRaisesRegex(ValueError, "32 byte"):
                kms.wrap_dek(b"too short")

    def test_missing_public_key_is_rebuilt_from_private_key(self):
        """Public key có thể phục hồi mà không thay private key đang bảo vệ phiếu."""
        with tempfile.TemporaryDirectory() as key_dir:
            kms = KMS(key_dir)
            kms.ensure_keys()
            wrapped_dek = kms.wrap_dek(b"c" * 32)
            (Path(key_dir) / "public_key.pem").unlink()

            restarted_kms = KMS(key_dir)
            restarted_kms.ensure_keys()

            self.assertTrue((Path(key_dir) / "public_key.pem").is_file())
            self.assertEqual(restarted_kms.unwrap_dek(wrapped_dek), b"c" * 32)

    def test_different_private_key_cannot_unwrap_dek(self):
        """Chỉ cặp private key đã bọc DEK mới có thể mở DEK đó."""
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_kms = KMS(first_dir)
            first_kms.ensure_keys()
            wrapped_dek = first_kms.wrap_dek(b"d" * 32)

            second_kms = KMS(second_dir)
            second_kms.ensure_keys()

            with self.assertRaises(ValueError):
                second_kms.unwrap_dek(wrapped_dek)


class VoteCryptoTests(unittest.TestCase):
    """Kiểm tra phiếu giả bằng KMS tạm, không dùng khóa thật."""

    def setUp(self):
        self.key_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.key_dir.cleanup)
        self.kms = KMS(self.key_dir.name)
        self.kms.ensure_keys()

    def test_encrypt_then_decrypt_returns_original_bytes(self):
        plaintext = b'{"ballot":{"candidate_id":2},"sig_ballot":"test"}'

        encrypted = encrypt_vote(plaintext, self.kms)

        self.assertEqual(set(encrypted), {"ciphertext", "wrapped_dek", "iv", "tag"})
        self.assertTrue(all(isinstance(value, bytes) for value in encrypted.values()))
        self.assertEqual(len(encrypted["iv"]), 12)
        self.assertEqual(len(encrypted["tag"]), 16)
        self.assertEqual(decrypt_vote(encrypted, self.kms), plaintext)

    def test_same_plaintext_gets_new_key_and_iv(self):
        first = encrypt_vote(b"same ballot", self.kms)
        second = encrypt_vote(b"same ballot", self.kms)

        self.assertNotEqual(
            self.kms.unwrap_dek(first["wrapped_dek"]),
            self.kms.unwrap_dek(second["wrapped_dek"]),
        )
        self.assertNotEqual(first["iv"], second["iv"])
        self.assertNotEqual(first["ciphertext"], second["ciphertext"])
        self.assertEqual(decrypt_vote(second, self.kms), b"same ballot")

    def test_modified_envelope_is_rejected(self):
        encrypted = encrypt_vote(b"ballot", self.kms)
        for field in ("ciphertext", "iv", "tag", "wrapped_dek"):
            with self.subTest(field=field):
                modified = encrypted.copy()
                modified[field] = bytes([encrypted[field][0] ^ 1]) + encrypted[field][1:]
                with self.assertRaises((InvalidTag, ValueError)):
                    decrypt_vote(modified, self.kms)

    def test_invalid_lengths_and_plaintext_type_are_rejected(self):
        with self.assertRaises(TypeError):
            encrypt_vote("ballot", self.kms)

        encrypted = encrypt_vote(b"ballot", self.kms)
        for field, invalid in (("iv", b"short"), ("tag", b"short")):
            with self.subTest(field=field):
                modified = encrypted.copy()
                modified[field] = invalid
                with self.assertRaises(ValueError):
                    decrypt_vote(modified, self.kms)


if __name__ == "__main__":
    unittest.main()
