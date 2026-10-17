"""
MỤC ĐÍCH: Kiểm tra toàn bộ schema request/response của API.
PHỤ THUỘC: unittest, Pydantic và app.api.schemas; không cần database.
LUỒNG: Tạo payload giả -> Pydantic kiểm tra -> xác nhận dữ liệu đúng/sai.
CÁCH CHẠY: python -m unittest tests.test_schemas -v
"""

import base64
import unittest

from pydantic import ValidationError

from app.api.schemas import (
    ActivationRequest,
    AdminLoginRequest,
    Ballot,
    CandidateResponse,
    LoginRequest,
    ResultItem,
    ResultResponse,
    TokenResponse,
    VoteRequest,
    VoteResponse,
)


class AccountSchemaTests(unittest.TestCase):
    def test_activation_request_accepts_valid_payload(self):
        request = ActivationRequest(
            voter_id="SV001",
            activation_code="activation-code",
            password="password123",
            public_key="-----BEGIN PUBLIC KEY-----",
        )

        self.assertEqual(request.voter_id, "SV001")

    def test_activation_request_rejects_invalid_voter_id(self):
        for voter_id in ("", "SV 001", "SV@001", "A" * 21):
            with self.subTest(voter_id=voter_id):
                with self.assertRaises(ValidationError):
                    ActivationRequest(
                        voter_id=voter_id,
                        activation_code="activation-code",
                        password="password123",
                        public_key="public-key",
                    )

    def test_activation_request_rejects_short_password(self):
        with self.assertRaises(ValidationError):
            ActivationRequest(
                voter_id="SV001",
                activation_code="activation-code",
                password="short",
                public_key="public-key",
            )

    def test_activation_request_rejects_extra_field(self):
        with self.assertRaises(ValidationError):
            ActivationRequest(
                voter_id="SV001",
                activation_code="activation-code",
                password="password123",
                public_key="public-key",
                private_key="must-not-reach-server",
            )

    def test_login_request_rejects_missing_password(self):
        with self.assertRaises(ValidationError):
            LoginRequest(voter_id="SV001")

    def test_login_requests_accept_expected_fields(self):
        voter_login = LoginRequest(voter_id="SV001", password="password123")
        admin_login = AdminLoginRequest(username="admin", password="password123")

        self.assertEqual(voter_login.voter_id, "SV001")
        self.assertEqual(admin_login.username, "admin")


class ElectionSchemaTests(unittest.TestCase):
    def test_token_response_accepts_bearer_and_ascii_election_id(self):
        response = TokenResponse(access_token="jwt", election_id="election-2026")

        self.assertEqual(response.token_type, "bearer")

    def test_token_response_rejects_wrong_type_and_non_ascii_election_id(self):
        for payload in (
            {"access_token": "jwt", "token_type": "basic", "election_id": "election-2026"},
            {"access_token": "jwt", "election_id": "bầu-cử-2026"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    TokenResponse(**payload)

    def test_candidate_response_accepts_optional_party(self):
        response = CandidateResponse(candidate_id=1, name="Nguyen Van A", party=None)

        self.assertIsNone(response.party)

    def test_candidate_response_rejects_sensitive_extra_field(self):
        with self.assertRaises(ValidationError):
            CandidateResponse(
                candidate_id=1,
                name="Nguyen Van A",
                party=None,
                ciphertext="must-not-be-returned",
            )

    def test_ballot_accepts_strict_values(self):
        ballot = Ballot(
            candidate_id=1,
            nonce="0123456789abcdef0123456789abcdef",
            ts=1_700_000_000,
        )

        self.assertEqual(ballot.candidate_id, 1)

    def test_ballot_rejects_invalid_nonce_and_non_integer_values(self):
        invalid_payloads = (
            {"candidate_id": True, "nonce": "0" * 32, "ts": 1_700_000_000},
            {"candidate_id": 1, "nonce": "ABCDEF" * 5 + "AB", "ts": 1_700_000_000},
            {"candidate_id": 1, "nonce": "0" * 32, "ts": 1.5},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    Ballot(**payload)


class VoteSchemaTests(unittest.TestCase):
    def setUp(self):
        self.ballot = Ballot(
            candidate_id=1,
            nonce="0123456789abcdef0123456789abcdef",
            ts=1_700_000_000,
        )
        self.signature = base64.b64encode(b"demo-signature").decode("ascii")

    def test_vote_request_accepts_base64_signatures(self):
        request = VoteRequest(
            ballot=self.ballot,
            sig_ballot=self.signature,
            sig_cast=self.signature,
        )

        self.assertEqual(request.sig_ballot, self.signature)
        self.assertEqual(request.sig_cast, self.signature)

    def test_vote_request_rejects_invalid_base64(self):
        invalid_signatures = (
            ("khong phai base64!", self.signature),
            (self.signature, "sai!"),
        )
        for sig_ballot, sig_cast in invalid_signatures:
            with self.subTest(sig_ballot=sig_ballot, sig_cast=sig_cast):
                with self.assertRaises(ValidationError):
                    VoteRequest(
                        ballot=self.ballot,
                        sig_ballot=sig_ballot,
                        sig_cast=sig_cast,
                    )

    def test_vote_response_requires_sha256_hex_receipt(self):
        response = VoteResponse(receipt="a" * 64)

        self.assertTrue(response.success)
        with self.assertRaises(ValidationError):
            VoteResponse(receipt="xyz")


class ResultSchemaTests(unittest.TestCase):
    def test_result_response_accepts_non_negative_counts(self):
        response = ResultResponse(
            results=[
                ResultItem(candidate_id=1, name="Nguyen Van A", votes=2),
                ResultItem(candidate_id=2, name="Tran Thi B", votes=0),
            ],
            total_votes=2,
        )

        self.assertEqual(response.total_votes, 2)
        self.assertEqual(len(response.results), 2)

    def test_result_response_rejects_negative_or_boolean_counts(self):
        invalid_payloads = (
            {"results": [{"candidate_id": 1, "name": "A", "votes": -1}], "total_votes": 0},
            {"results": [{"candidate_id": 1, "name": "A", "votes": True}], "total_votes": 1},
            {"results": [], "total_votes": True},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    ResultResponse(**payload)


if __name__ == "__main__":
    unittest.main()
