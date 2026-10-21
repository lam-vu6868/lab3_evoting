"""
MỤC ĐÍCH: Kiểm tra route kích hoạt chỉ lưu khóa công khai và trả thành công sau commit.
PHỤ THUỘC: unittest; session giả, không ghi PostgreSQL.
LUỒNG: Gửi yêu cầu SV001, kiểm tra mã, khóa dòng, ghi trạng thái và lỗi rollback.
TỰ KIỂM TRA: python -m unittest tests.test_activate -v
"""

import os
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException


TEST_ENV = {
    "JWT_SECRET": "test-only-secret-not-used-outside-tests",
    "APP_DATABASE_URL": "postgresql+asyncpg://app_user:test@127.0.0.1:5433/evoting",
    "ADMIN_DATABASE_URL": "postgresql+asyncpg://admin_app:test@127.0.0.1:5433/evoting",
    "TALLY_DATABASE_URL": "postgresql+asyncpg://tally_user:test@127.0.0.1:5433/evoting",
    "ADMIN_USERNAME": "test-admin",
    "ADMIN_PASSWORD": "test-password",
    "ELECTION_ID": "test-election",
    "ELECTION_START": "2026-01-01T00:00:00Z",
    "ELECTION_END": "2026-12-31T23:59:59Z",
}

with patch.dict(os.environ, TEST_ENV):
    from app.api.schemas import ActivationRequest
    from app.auth.activate import activate
    from app.auth.auth import hash_activation_code
    from app.main import app


class FakeSession:
    def __init__(self, voter, *, fail_commit=False):
        self.voter = voter
        self.fail_commit = fail_commit
        self.saved_status = None
        self.committed = False
        self.locked = False

    @asynccontextmanager
    async def begin(self):
        old = dict(vars(self.voter)) if self.voter else None
        try:
            yield self
            if self.fail_commit:
                raise RuntimeError("commit failed")
            self.committed = True
        except Exception:
            if old is not None:
                vars(self.voter).update(old)
            self.saved_status = None
            raise

    async def execute(self, statement):
        self.locked = statement._for_update_arg is not None
        return SimpleNamespace(scalar_one_or_none=lambda: self.voter)

    def add(self, status):
        self.saved_status = status


class ActivateTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

    def setUp(self):
        self.voter = SimpleNamespace(
            voter_id="SV001", activated=False,
            activation_hash=hash_activation_code("fake-code"),
            password_hash=None, salt=None, public_key=None,
        )
        self.session = FakeSession(self.voter)

        self.payload = {
            "voter_id": "SV001", "activation_code": "fake-code",
            "password": "password-for-test", "public_key": self.public_key,
        }

    async def test_activate_commits_voter_and_status(self):
        response = await activate(ActivationRequest(**self.payload), self.session)
        self.assertEqual(response, {"success": True})
        self.assertTrue(self.session.locked)
        self.assertTrue(self.session.committed)
        self.assertTrue(self.voter.activated)
        self.assertIsNone(self.voter.activation_hash)
        self.assertEqual(self.voter.public_key, self.public_key)
        self.assertIsNotNone(self.voter.password_hash)
        self.assertIsNotNone(self.voter.salt)
        self.assertEqual(self.session.saved_status.voter_id, "SV001")

    async def test_wrong_code_and_second_activation_do_not_write(self):
        wrong = dict(self.payload, activation_code="wrong")
        with self.assertRaises(HTTPException) as error:
            await activate(ActivationRequest(**wrong), self.session)
        self.assertEqual(error.exception.status_code, 400)
        self.assertFalse(self.session.committed)
        self.assertIsNone(self.session.saved_status)
        self.voter.activated = True
        with self.assertRaises(HTTPException) as error:
            await activate(ActivationRequest(**self.payload), self.session)
        self.assertEqual(error.exception.status_code, 400)
        self.assertIsNone(self.session.saved_status)

    async def test_invalid_public_key_is_rejected_before_write(self):
        bad = dict(self.payload, public_key="not a PEM key")
        with self.assertRaises(HTTPException) as error:
            await activate(ActivationRequest(**bad), self.session)
        self.assertEqual(error.exception.status_code, 400)
        self.assertFalse(self.session.committed)

    async def test_commit_error_never_returns_success(self):
        self.session.fail_commit = True
        with self.assertRaisesRegex(RuntimeError, "commit failed"):
            await activate(ActivationRequest(**self.payload), self.session)
        self.assertFalse(self.voter.activated)
        self.assertIsNone(self.session.saved_status)

    async def test_main_registers_activate_route(self):
        self.assertTrue(any(route.path == "/activate" and "POST" in route.methods for route in app.routes))


if __name__ == "__main__":
    unittest.main()
