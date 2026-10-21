"""
FILE: app/voting/voting_service.py
TRẠNG THÁI: Đã triển khai kiểm tra chữ ký, mã hóa và ba thay đổi DB trong transaction của route.
MỤC ĐÍCH: Điều phối một lần bỏ phiếu, không tự commit hoặc trả HTTP response.
PHỤ THUỘC: models, signature_service, crypto_service, KMS, AsyncSession từ route /vote.
LUỒNG: Kiểm thời gian/voter/candidate/chữ ký; khóa voter_status; INSERT nonce và vote;
cập nhật trạng thái và trả receipt. Route commit xong mới trả thành công.
TỰ KIỂM TRA: STAGE5_TEST_DB_NAME=... python -m unittest tests.test_voting -v trên DB riêng.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import VoteRequest
from app.core.config import Settings
from app.crypto.crypto_service import encrypt_vote
from app.crypto.kms import KMS
from app.crypto.signature_service import (
    build_cast, decode_signature, load_voter_public_key, verify_signature,
)
from app.database.models import Candidate, UsedNonce, Vote, Voter, VoterStatus


class VotingError(ValueError):
    """Lỗi nghiệp vụ để route ánh xạ sang mã HTTP sau rollback."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def cast_vote(
    session: AsyncSession, voter_id: str, request: VoteRequest, settings: Settings, kms: KMS
) -> str:
    """Ghi một lá phiếu; caller phải mở transaction trước và commit sau hàm này."""
    now = datetime.now(timezone.utc)
    if not settings.ELECTION_START <= now < settings.ELECTION_END:
        raise VotingError(403, "Ngoài thời gian bỏ phiếu")
    if abs(now.timestamp() - request.ballot.ts) > settings.VOTE_REQUEST_MAX_AGE_SECONDS:
        raise VotingError(400, "Yêu cầu bỏ phiếu đã quá hạn hoặc ở tương lai")

    voter = (await session.execute(select(Voter).where(Voter.voter_id == voter_id))).scalar_one_or_none()
    if voter is None or not voter.activated or not voter.public_key:
        raise VotingError(400, "Cử tri chưa được kích hoạt")
    candidate = (await session.execute(
        select(Candidate.candidate_id).where(Candidate.candidate_id == request.ballot.candidate_id)
    )).scalar_one_or_none()
    if candidate is None:
        raise VotingError(400, "Ứng viên không hợp lệ")

    ballot = request.ballot.model_dump()
    try:
        cast = build_cast(settings.ELECTION_ID, voter_id, ballot["nonce"], ballot["ts"])
        public_key = load_voter_public_key(voter.public_key)
        ballot_signature = decode_signature(request.sig_ballot)
        cast_signature = decode_signature(request.sig_cast)
        valid = (
            verify_signature(public_key, ballot, ballot_signature)
            and verify_signature(public_key, cast, cast_signature)
        )
    except ValueError as error:
        raise VotingError(400, "Chữ ký hoặc lá phiếu không hợp lệ") from error
    if not valid:
        raise VotingError(400, "Chữ ký hoặc lá phiếu không hợp lệ")

    status = (await session.execute(
        select(VoterStatus).where(VoterStatus.voter_id == voter_id).with_for_update()
    )).scalar_one_or_none()
    if status is None:
        raise VotingError(500, "Không thể ghi phiếu")
    if status.has_voted:
        raise VotingError(409, "Cử tri đã bỏ phiếu")

    await session.execute(insert(UsedNonce).inline().values(nonce=ballot["nonce"]))
    envelope = json.dumps(
        {"ballot": ballot, "sig_ballot": request.sig_ballot},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    encrypted = encrypt_vote(envelope, kms)
    await session.execute(insert(Vote).inline().values(vote_id=uuid.uuid4(), **encrypted))

    receipt_hash = hashlib.sha256(cast_signature).digest()
    status.has_voted = True
    status.sig_cast = cast_signature
    status.receipt_hash = receipt_hash
    status.voted_at = now.replace(minute=0, second=0, microsecond=0)
    return receipt_hash.hex()
