"""Kiểm tra HTTP và quyền DB với dữ liệu giả trên PostgreSQL thử nghiệm riêng.

Đặt STAGE8_TEST_DB_NAME=evoting_stage5_test_... (hoặc evoting_stage8_test_...)
rồi chạy python -m unittest tests.test_attack -v. Test khởi động backend local,
tạo cử tri giả, kiểm tra phản hồi và số phiếu; dữ liệu giả được giữ trong DB test.
KMS tạm sẽ bị xóa sau test, nên DB thử này chỉ dùng kiểm bỏ phiếu, không kiểm phiếu.
Không dùng database evoting và không in mã kích hoạt, JWT hay mật khẩu.
"""

import asyncio
import base64
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.auth import hash_activation_code
from app.core.config import Settings
from app.crypto.signature_service import build_ballot, build_cast, canonical_bytes
from app.database.models import Vote, Voter


ROOT = Path(__file__).resolve().parents[1]


class AttackIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database_name = os.environ.get("STAGE8_TEST_DB_NAME", "")
        if re.fullmatch(r"evoting_stage(?:5|8)_test_[a-z0-9_]+", database_name) is None:
            raise unittest.SkipTest("Cần STAGE8_TEST_DB_NAME trỏ tới DB thử nghiệm riêng")

        config = Settings()
        cls.app_url = make_url(config.APP_DATABASE_URL).set(database=database_name)
        cls.admin_url = make_url(config.ADMIN_DATABASE_URL).set(database=database_name)
        cls.tally_url = make_url(config.TALLY_DATABASE_URL).set(database=database_name)
        if any(url.host != "127.0.0.1" or url.port != 5433
               for url in (cls.app_url, cls.admin_url, cls.tally_url)):
            raise unittest.SkipTest("Test chỉ dùng PostgreSQL local tại 127.0.0.1:5433")
        cls.admin_username = config.ADMIN_USERNAME
        cls.admin_password = config.ADMIN_PASSWORD
        cls.election_id = "stage8-attack-test"
        cls.keys = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.keys.cleanup)

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        cls.base_url = f"http://127.0.0.1:{port}"
        now = datetime.now(timezone.utc)
        env = os.environ.copy()
        env.update({
            "APP_DATABASE_URL": cls.app_url.render_as_string(hide_password=False),
            "ADMIN_DATABASE_URL": cls.admin_url.render_as_string(hide_password=False),
            "TALLY_DATABASE_URL": cls.tally_url.render_as_string(hide_password=False),
            "KMS_KEY_DIR": cls.keys.name,
            "ELECTION_ID": cls.election_id,
            "ELECTION_START": (now - timedelta(hours=1)).isoformat(),
            "ELECTION_END": (now + timedelta(hours=1)).isoformat(),
        })
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--no-access-log"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cls.addClassCleanup(cls.stop_server)
        for _ in range(60):
            if cls.server.poll() is not None:
                raise RuntimeError("Backend thử nghiệm không khởi động được")
            try:
                status, _ = cls.http("GET", "/candidates")
                if status == 200:
                    break
            except URLError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("Backend thử nghiệm không sẵn sàng")

    @classmethod
    def stop_server(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait(timeout=5)

    @classmethod
    def http(cls, method, path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            cls.base_url + path, method=method, headers=headers,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
        )
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    @classmethod
    def db_call(cls, url, operation):
        async def run():
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    return await operation(connection)
            finally:
                await engine.dispose()
        return asyncio.run(run())

    @classmethod
    def count_votes(cls):
        async def count(connection):
            return await connection.scalar(select(func.count()).select_from(Vote))
        return cls.db_call(cls.tally_url, count)

    def create_voter(self):
        voter_id = "AT" + secrets.token_hex(8)
        code = secrets.token_urlsafe(32)
        password = "fake-password-123"
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("ascii")

        async def insert(connection):
            await connection.execute(Voter.__table__.insert().values(
                voter_id=voter_id, full_name="Cử tri kiểm thử", activation_hash=hash_activation_code(code),
                activated=False,
            ))
        self.db_call(self.app_url, insert)
        body = {"voter_id": voter_id, "activation_code": code,
                "password": password, "public_key": public_key}
        return voter_id, key, body

    def activate_and_login(self):
        voter_id, key, activation = self.create_voter()
        self.assertEqual(self.http("POST", "/activate", activation)[0], 200)
        status, login = self.http("POST", "/login", {
            "voter_id": voter_id, "password": activation["password"]
        })
        self.assertEqual(status, 200)
        self.assertEqual(login["election_id"], self.election_id)
        return voter_id, key, activation, login["access_token"]

    def signed_vote(self, voter_id, key, ts=None):
        ts = int(time.time()) if ts is None else ts
        nonce = secrets.token_hex(16)
        ballot = build_ballot(2, nonce, ts)
        cast = build_cast(self.election_id, voter_id, nonce, ts)

        def sign(payload):
            signature = key.sign(canonical_bytes(payload), padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
            return base64.b64encode(signature).decode("ascii")

        return {"ballot": ballot, "sig_ballot": sign(ballot), "sig_cast": sign(cast)}

    def test_activation_login_and_input_rejection(self):
        before = self.count_votes()
        voter_id, _, activation, token = self.activate_and_login()
        self.assertTrue(token)
        self.assertEqual(self.http("POST", "/activate", activation)[0], 400)
        self.assertEqual(self.http("POST", "/login", {
            "voter_id": voter_id, "password": "wrong-password"
        })[0], 401)
        self.assertEqual(self.http("POST", "/login", {
            "voter_id": "' OR 1=1 --", "password": "wrong-password"
        })[0], 422)
        self.assertEqual(self.count_votes(), before)

    def test_roles_and_early_results(self):
        before = self.count_votes()
        _, _, _, voter_token = self.activate_and_login()
        self.assertEqual(self.http("GET", "/results")[0], 401)
        self.assertEqual(self.http("GET", "/results", token=voter_token)[0], 403)
        status, admin = self.http("POST", "/admin/login", {
            "username": self.admin_username, "password": self.admin_password
        })
        self.assertEqual(status, 200)
        self.assertEqual(self.http("GET", "/results", token=admin["access_token"])[0], 403)
        self.assertEqual(self.count_votes(), before)

    def test_bad_signatures_and_times_leave_no_vote(self):
        before = self.count_votes()
        voter_id, key, _, token = self.activate_and_login()
        for ts in (int(time.time()) - 600, int(time.time()) + 600):
            self.assertEqual(self.http("POST", "/vote", self.signed_vote(voter_id, key, ts), token)[0], 400)
        valid = self.signed_vote(voter_id, key)
        for field in ("sig_ballot", "sig_cast"):
            invalid = dict(valid, **{field: base64.b64encode(b"0" * 256).decode("ascii")})
            self.assertEqual(self.http("POST", "/vote", invalid, token)[0], 400)
        self.assertEqual(self.count_votes(), before)

    def test_replay_commits_only_once(self):
        before = self.count_votes()
        voter_id, key, _, token = self.activate_and_login()
        request = self.signed_vote(voter_id, key)
        status, response = self.http("POST", "/vote", request, token)
        self.assertEqual(status, 200)
        self.assertTrue(response["success"])
        self.assertEqual(self.http("POST", "/vote", request, token)[0], 409)
        self.assertEqual(self.count_votes(), before + 1)

    def test_database_roles_cannot_read_or_modify_votes(self):
        async def admin_read(connection):
            await connection.execute(text("SELECT 1 FROM votes LIMIT 0"))

        async def tally_write(connection):
            await connection.execute(text("UPDATE votes SET tag=tag WHERE false"))

        for url, operation in ((self.admin_url, admin_read), (self.tally_url, tally_write)):
            with self.subTest(role=url.username):
                with self.assertRaises(DBAPIError) as error:
                    self.db_call(url, operation)
                self.assertEqual(error.exception.orig.sqlstate, "42501")


if __name__ == "__main__":
    unittest.main()
