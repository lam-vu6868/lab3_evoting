"""
FILE: tests/test_crypto.py
TRẠNG THÁI: Đã kiểm tra KMS, AES-GCM và chữ ký Python; WebCrypto, password và JWT chưa triển khai.
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

import base64
import tempfile
import unittest
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.crypto.crypto_service import decrypt_vote, encrypt_vote
from app.crypto.kms import KMS
from app.crypto.signature_service import (
    build_ballot,
    build_cast,
    canonical_bytes,
    decode_signature,
    load_voter_public_key,
    verify_signature,
)


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


class SignatureTests(unittest.TestCase):
    """Khóa cử tri trong test chỉ ở RAM; backend chỉ dùng public key."""

    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_pem = cls.private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

    def test_canonical_ballot_and_cast_match_protocol(self):
        nonce = "a" * 32
        ballot = build_ballot(2, nonce, 1760000000)
        cast = build_cast("election-1", "SV001", nonce, 1760000000)

        self.assertEqual(
            canonical_bytes(ballot),
            b'{"candidate_id":2,"nonce":"' + nonce.encode() + b'","ts":1760000000}',
        )
        self.assertEqual(
            canonical_bytes(cast),
            b'{"election_id":"election-1","nonce":"' + nonce.encode()
            + b'","ts":1760000000,"voter_id":"SV001"}',
        )

    def test_rejects_payloads_that_could_sign_different_bytes(self):
        valid = build_ballot(2, "a" * 32, 1760000000)
        invalid = [
            {**valid, "candidate_id": True},
            {**valid, "ts": 1.5},
            {**valid, "ts": 2**53},
            {**valid, "nonce": "A" * 32},
            {**valid, "extra": "unexpected"},
            build_cast("election-1", "SV001", "a" * 32, 1760000000)
            | {"voter_id": "SVé"},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                canonical_bytes(payload)

    def test_valid_signature_and_changed_ballot_or_key(self):
        ballot = build_ballot(2, "a" * 32, 1760000000)
        signature = self.private_key.sign(
            canonical_bytes(ballot),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        public_key = load_voter_public_key(self.public_pem)
        encoded = base64.b64encode(signature).decode("ascii")

        self.assertEqual(decode_signature(encoded), signature)
        self.assertTrue(verify_signature(public_key, ballot, signature))
        self.assertFalse(verify_signature(public_key, {**ballot, "candidate_id": 3}, signature))
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.assertFalse(verify_signature(other_key.public_key(), ballot, signature))

    def test_cast_signature_covers_election_voter_nonce_and_time(self):
        cast = build_cast("election-1", "SV001", "a" * 32, 1760000000)
        signature = self.private_key.sign(
            canonical_bytes(cast),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        public_key = load_voter_public_key(self.public_pem)

        self.assertTrue(verify_signature(public_key, cast, signature))
        for field, changed in (
            ("election_id", "election-2"),
            ("voter_id", "SV002"),
            ("nonce", "b" * 32),
            ("ts", 1760000001),
        ):
            with self.subTest(field=field):
                self.assertFalse(verify_signature(public_key, {**cast, field: changed}, signature))

    def test_rejects_invalid_public_key_and_base64(self):
        with self.assertRaises(ValueError):
            load_voter_public_key("-----BEGIN RSA PUBLIC KEY-----\ninvalid\n-----END RSA PUBLIC KEY-----")
        for encoded in ("%%%", "YQ==", "A" * 344):
            with self.subTest(encoded=encoded[:8]), self.assertRaises(ValueError):
                decode_signature(encoded)


if __name__ == "__main__":
    unittest.main()
