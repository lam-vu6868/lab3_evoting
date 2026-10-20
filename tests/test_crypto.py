"""
FILE: tests/test_crypto.py
TRẠNG THÁI: Đã kiểm tra KMS, AES-GCM, WebCrypto, mật khẩu, mã kích hoạt, JWT, Bearer và admin.
MỤC ĐÍCH: Test hàm mật mã và xác thực, không cần PostgreSQL.
PHỤ THUỘC: unittest, tempfile; kms, crypto_service, signature_service, auth.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Viết unittest.TestCase; dùng TemporaryDirectory cho KMS, không dùng volume khóa thật.
2. Test AES round-trip, sửa ciphertext/tag/IV/wrapped key; restart KMS dùng cùng khóa.
3. Sinh khóa cử tri tạm trong test, ký RSA-PSS salt 32 rồi verify; đổi candidate/nonce/ts.
4. Có vector JSON/chữ ký cố định xuất từ WebCrypto để kiểm tương thích JS/Python.
5. Test mật khẩu, mã kích hoạt, JWT, Bearer và đối chiếu admin đúng/sai.
6. Guard unittest.main() để chạy python -m unittest tests.test_crypto.

TỰ KIỂM TRA:
Không có khóa thật trong fixture/Git; từng test xác minh hành vi, không chỉ mock mọi hàm để luôn pass.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

import base64
import tempfile
import time
import unittest
from pathlib import Path
from secrets import token_urlsafe
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from pydantic import ValidationError
from starlette.requests import Request

from app.auth.auth import (
    create_jwt,
    hash_activation_code,
    hash_password,
    require_admin,
    require_voter,
    verify_activation_code,
    verify_admin_credentials,
    verify_jwt,
    verify_password,
)
from app.core.config import Settings
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

    def test_browser_webcrypto_vector_matches_python(self):
        """Vector từ browser thật chỉ giữ public key và hai chữ ký giả."""
        public_pem = (
            "-----BEGIN PUBLIC KEY-----\n"
            "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv9pyygVbPOEhSZo7SKOh\n"
            "zFAc6bxlnUr+Q+qyYpTupa3x607b71uSqEm3/xJKaRGLrQjp0crPzAONGtpERgDa\n"
            "j5+1E5K5GY/Z4ijK0wqBXh4JfRP0ilXiQvtWhUFyqo9Yp0xL96iyWjm5uBz6l7lS\n"
            "8sxdQImjT2977gM0fJW3ArxBG4zmUybA4vOwYtEvpzijj3xJUwPH9WebtXCqc86S\n"
            "fF+5hj9vEeNhVnM3d87TqoYMvfJ/AxHGcHYvdOm4CfEiC+DqMIvrwjPekPo55fCR\n"
            "YxhSoIp+FqhZnBGxCfau5nG9yTQxep0F5OlAd1EAT9uIsViFiZkgkY3MoXrBqijF\n"
            "BwIDAQAB\n"
            "-----END PUBLIC KEY-----\n"
        )
        sig_ballot = (
            "FfGFIglNcGHKCzcIUiJVkI6sYa7MFYqMYGYIftwPMBD6NN7xhlRu8e7I6Zaj/PwrHlWns0za7MCK"
            "MDmdheBKVHQONOh7Zs2VdGyHOYC728PQKkBBdcqxbQpyN1DhHt9fuP2btmN6d58Ki5wBurpmpltK"
            "S2c24LrBogYI0c5T9uz5lvFky4sP5uJ5zn77iZM5B40JM28YZGe9FmkE3Mts244tcehLQt8kx0Pj"
            "OSUiXsc8r9Zonomk1B/7YHi5ukzMDpYCwWNE8VL2y4dH1phWkZFfEzNgKwWNMvWzI7/6gRBXqFLI"
            "Xg8w8CYErP1IfdyCrDYA2nfBIIw/HyeI8eej4g=="
        )
        sig_cast = (
            "dZShCzsqVabrYHE6/d4VpDSJXlfyY7SFMHINBGzImZNJYF61HjB7J5jbVMoUoiIPo6AE6mL/hakQ"
            "lVLcNgItz9MXAHwH0BVsuip5JQ9EfEk+jHG7x6D1L5r3SCEITWlB3OFBELxBBzwmleOssCmdG0AJ"
            "p4/NuSIduOmcXV68vWIaVlEydK2pdwTa4bFeCyLxkeIU9u05u8jf8b0j4agwmR27Vrd3rGUqeFH4"
            "hY/zBWhkkeBSv0C03XY2Y+KWr70I5egHfsJbYHzI/Pch6cCWi47Q2MIYQzVjmpRQVhRRm42WXQUw"
            "/SkaBgXwoCQ+Ty3slo7n9AVqVS3ID3s/uinbAw=="
        )
        public_key = load_voter_public_key(public_pem)
        ballot = build_ballot(2, "a" * 32, 1760000000)
        cast = build_cast("election-1", "SV001", "a" * 32, 1760000000)

        self.assertTrue(verify_signature(public_key, ballot, decode_signature(sig_ballot)))
        self.assertTrue(verify_signature(public_key, cast, decode_signature(sig_cast)))
        self.assertFalse(verify_signature(
            public_key, {**ballot, "candidate_id": 3}, decode_signature(sig_ballot)
        ))
        self.assertFalse(verify_signature(
            public_key, {**cast, "voter_id": "SV002"}, decode_signature(sig_cast)
        ))


class ActivationCodeTests(unittest.TestCase):
    """Dùng mã ngẫu nhiên giả trong RAM; không đụng dữ liệu cử tri thật."""

    def test_code_hash_is_stable_and_wrong_code_fails(self):
        code = token_urlsafe(32)
        stored_hash = hash_activation_code(code)

        self.assertIsInstance(stored_hash, bytes)
        self.assertEqual(len(stored_hash), 32)
        self.assertEqual(hash_activation_code(code), stored_hash)
        self.assertEqual(
            hash_activation_code("abc").hex(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
        self.assertTrue(verify_activation_code(code, stored_hash))
        self.assertFalse(verify_activation_code(code + "x", stored_hash))

    def test_invalid_code_or_stored_hash_is_rejected(self):
        for code in ("", "a" * 257, "bad-\ud800", None):
            with self.subTest(code=repr(code)), self.assertRaises(ValueError):
                hash_activation_code(code)
        self.assertFalse(verify_activation_code("test-code", b"short"))
        self.assertFalse(verify_activation_code("", b"0" * 32))
        self.assertFalse(verify_activation_code("test-code", None))


class PasswordTests(unittest.TestCase):
    """Kiểm tra hash bằng mật khẩu giả; không đọc hay ghi bảng voters."""

    def test_same_password_has_independent_salts_and_hashes(self):
        with patch("app.auth.auth.get_settings", return_value=SimpleNamespace(PBKDF2_ITERATIONS=600000)):
            first_hash, first_salt = hash_password("mat-khau-gia-123")
            second_hash, second_salt = hash_password("mat-khau-gia-123")

        self.assertEqual(len(first_salt), 16)
        self.assertNotEqual(first_salt, second_salt)
        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(first_hash.startswith(b"pbkdf2_sha256$600000$"))
        self.assertTrue(verify_password("mat-khau-gia-123", first_hash, first_salt))

    def test_verify_uses_iterations_saved_in_hash(self):
        with patch("app.auth.auth.get_settings", return_value=SimpleNamespace(PBKDF2_ITERATIONS=600000)):
            encoded_hash, salt = hash_password("mat-khau-gia-123")
        with patch("app.auth.auth.get_settings", return_value=SimpleNamespace(PBKDF2_ITERATIONS=700000)):
            self.assertTrue(verify_password("mat-khau-gia-123", encoded_hash, salt))

    def test_wrong_password_or_corrupt_hash_is_rejected(self):
        with patch("app.auth.auth.get_settings", return_value=SimpleNamespace(PBKDF2_ITERATIONS=600000)):
            encoded_hash, salt = hash_password("mat-khau-gia-123")

        self.assertFalse(verify_password("sai-mat-khau", encoded_hash, salt))
        self.assertFalse(verify_password("mat-khau-gia-123", encoded_hash, b"short"))
        self.assertFalse(verify_password("mat-khau-gia-123", encoded_hash, b"0" * 16))
        self.assertFalse(verify_password("mat-khau-gia-123", b"bad-format", salt))
        self.assertFalse(verify_password(
            "mat-khau-gia-123", b"pbkdf2_sha256$600000$" + b"g" * 64, salt
        ))
        self.assertFalse(verify_password(
            "mat-khau-gia-123", b"pbkdf2_sha256$10000001$" + b"0" * 64, salt
        ))

    def test_hash_rejects_invalid_password(self):
        with self.assertRaises(ValueError):
            hash_password("")
        with self.assertRaises(ValueError):
            hash_password("a" * 129)
        with self.assertRaises(ValueError):
            hash_password("mat-khau-\ud800")
        self.assertFalse(verify_password(
            "mat-khau-\ud800", b"pbkdf2_sha256$1$" + b"0" * 64, b"0" * 16
        ))

    def test_settings_rejects_out_of_range_iterations(self):
        for iterations in (1000, 10_000_001):
            with self.subTest(iterations=iterations), self.assertRaises(ValidationError) as error:
                Settings(_env_file=None, PBKDF2_ITERATIONS=iterations)
            self.assertIn(("PBKDF2_ITERATIONS",), [item["loc"] for item in error.exception.errors()])


class JWTTests(unittest.TestCase):
    """Token thử được ký bằng secret giả, không dùng tài khoản hay DB thật."""

    secret = "test-jwt-secret-" + "x" * 32

    def test_voter_and_admin_token_round_trip(self):
        settings = SimpleNamespace(JWT_SECRET=self.secret, JWT_EXPIRE_MINUTES=60)
        with patch("app.auth.auth.get_settings", return_value=settings):
            for subject, role in (("SV001", "voter"), ("admin", "admin")):
                with self.subTest(role=role):
                    token = create_jwt(subject, role)
                    claims = verify_jwt(token)
                    self.assertEqual(claims["sub"], subject)
                    self.assertEqual(claims["role"], role)
                    self.assertEqual(claims["exp"] - claims["iat"], 3600)

    def test_expired_tampered_wrong_algorithm_and_missing_claims_fail(self):
        settings = SimpleNamespace(JWT_SECRET=self.secret, JWT_EXPIRE_MINUTES=60)
        now = int(time.time())
        claims = {"sub": "SV001", "role": "voter", "iat": now - 120, "exp": now - 1}
        with patch("app.auth.auth.get_settings", return_value=settings):
            expired = jwt.encode(claims, self.secret, algorithm="HS256")
            with self.assertRaises(ValueError):
                verify_jwt(expired)

            valid = create_jwt("SV001", "voter")
            header, payload, signature = valid.split(".")
            altered = "A" if signature[0] != "A" else "B"
            with self.assertRaises(ValueError):
                verify_jwt(f"{header}.{payload}.{altered}{signature[1:]}")

            wrong_algorithm = jwt.encode({**claims, "exp": now + 60}, self.secret, algorithm="HS512")
            with self.assertRaises(ValueError):
                verify_jwt(wrong_algorithm)

            for missing in ("sub", "role", "iat", "exp"):
                with self.subTest(missing=missing):
                    incomplete = {**claims, "exp": now + 60}
                    incomplete.pop(missing)
                    token = jwt.encode(incomplete, self.secret, algorithm="HS256")
                    with self.assertRaises(ValueError):
                        verify_jwt(token)

    def test_invalid_roles_subjects_and_time_claims_fail(self):
        settings = SimpleNamespace(JWT_SECRET=self.secret, JWT_EXPIRE_MINUTES=60)
        now = int(time.time())
        with patch("app.auth.auth.get_settings", return_value=settings):
            for subject, role in (("", "voter"), ("SV001", "guest")):
                with self.subTest(subject=subject, role=role), self.assertRaises(ValueError):
                    create_jwt(subject, role)

            valid = {"sub": "SV001", "role": "voter", "iat": now, "exp": now + 60}
            for changed in (
                {"role": "guest"}, {"sub": ""}, {"iat": str(now)},
                {"exp": str(now + 60)}, {"iat": now + 120}, {"exp": now},
            ):
                with self.subTest(changed=changed):
                    token = jwt.encode({**valid, **changed}, self.secret, algorithm="HS256")
                    with self.assertRaises(ValueError):
                        verify_jwt(token)

    def test_settings_rejects_short_jwt_secret(self):
        with self.assertRaises(ValidationError) as error:
            Settings(_env_file=None, JWT_SECRET="short")
        self.assertIn(("JWT_SECRET",), [item["loc"] for item in error.exception.errors()])


class BearerDependencyTests(unittest.IsolatedAsyncioTestCase):
    """Dùng request và token giả; không truy vấn DB hay dùng route thật."""

    secret = "test-jwt-secret-" + "x" * 32

    async def test_bearer_header_and_role_dependencies(self):
        from app.auth.auth import bearer_scheme

        settings = SimpleNamespace(JWT_SECRET=self.secret, JWT_EXPIRE_MINUTES=60)
        with patch("app.auth.auth.get_settings", return_value=settings):
            voter_token = create_jwt("SV001", "voter")
            admin_token = create_jwt("admin", "admin")
            for token, expected, dependency in (
                (voter_token, "SV001", require_voter),
                (admin_token, "admin", require_admin),
            ):
                request = Request({
                    "type": "http",
                    "headers": [(b"authorization", f"Bearer {token}".encode("ascii"))],
                })
                credentials = await bearer_scheme(request)
                self.assertEqual(dependency(credentials), expected)

            for token, dependency in ((admin_token, require_voter), (voter_token, require_admin)):
                with self.assertRaises(HTTPException) as error:
                    dependency(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
                self.assertEqual(error.exception.status_code, 403)

            with self.assertRaises(HTTPException) as error:
                require_voter(HTTPAuthorizationCredentials(scheme="Basic", credentials=voter_token))
            self.assertEqual(error.exception.status_code, 401)

    async def test_missing_malformed_and_invalid_token_are_unauthorized(self):
        from app.auth.auth import bearer_scheme

        settings = SimpleNamespace(JWT_SECRET=self.secret, JWT_EXPIRE_MINUTES=60)
        with patch("app.auth.auth.get_settings", return_value=settings):
            for header in (None, b"Basic abc", b"Bearer", b"Bearer "):
                with self.subTest(header=header):
                    headers = [] if header is None else [(b"authorization", header)]
                    credentials = await bearer_scheme(Request({"type": "http", "headers": headers}))
                    with self.assertRaises(HTTPException) as error:
                        require_voter(credentials)
                    self.assertEqual(error.exception.status_code, 401)
                    self.assertEqual(error.exception.headers.get("WWW-Authenticate"), "Bearer")

            bad_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.value")
            with self.assertRaises(HTTPException) as error:
                require_admin(bad_credentials)
            self.assertEqual(error.exception.status_code, 401)


class AdminCredentialTests(unittest.TestCase):
    """So sánh với cấu hình giả; không đụng .env hoặc bảng voters."""

    def test_correct_and_wrong_credentials(self):
        settings = SimpleNamespace(ADMIN_USERNAME="admin-demo", ADMIN_PASSWORD="mat-khau-gia-123")
        with patch("app.auth.auth.get_settings", return_value=settings):
            self.assertTrue(verify_admin_credentials("admin-demo", "mat-khau-gia-123"))
            self.assertFalse(verify_admin_credentials("admin-khac", "mat-khau-gia-123"))
            self.assertFalse(verify_admin_credentials("admin-demo", "sai-mat-khau"))
            self.assertFalse(verify_admin_credentials("admin-khac", "sai-mat-khau"))

    def test_invalid_inputs_and_unicode_are_handled(self):
        settings = SimpleNamespace(ADMIN_USERNAME="quản-trị", ADMIN_PASSWORD="mật-khẩu-giả")
        with patch("app.auth.auth.get_settings", return_value=settings):
            self.assertTrue(verify_admin_credentials("quản-trị", "mật-khẩu-giả"))
            for username, password in (("", "mật-khẩu-giả"), ("quản-trị", ""),
                                       (None, "mật-khẩu-giả"), ("quản-trị", None),
                                       ("bad-\ud800", "mật-khẩu-giả")):
                with self.subTest(username=repr(username), password=repr(password)):
                    self.assertFalse(verify_admin_credentials(username, password))


if __name__ == "__main__":
    unittest.main()
