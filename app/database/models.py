"""
FILE: app/database/models.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Ánh xạ đúng 5 bảng SQL thành lớp Python, không tạo schema mới.
PHỤ THUỘC: app.database.database.Base; db/init.sql là nguồn chuẩn về cột và ràng buộc.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Voter: voter_id PK, full_name, activation_hash, activated, password_hash, salt, public_key, created_at.
2. Candidate: candidate_id PK, name, party.
3. Vote: vote_id UUID PK, ciphertext, wrapped_dek, iv, tag; tuyệt đối không thêm voter_id/timestamp.
4. VoterStatus: voter_id PK/FK voters, has_voted, sig_cast, receipt_hash, voted_at.
5. UsedNonce: nonce PK, used_at. BYTEA dùng LargeBinary; TIMESTAMPTZ timezone=True.
6. Khớp nullable/default/check constraint của SQL. Đừng thêm quan hệ nối voter với Vote.
7. Phiếu được INSERT bằng Core insert(...).inline(), UUID truyền từ uuid.uuid4();
   tránh ORM tự RETURNING vì app_user không có SELECT votes.

TỰ KIỂM TRA:
Đối chiếu từng cột với init.sql; không thay tên cột; thử INSERT 
phiếu bằng quyền app_user thực.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
# uuid là thư viện có sẵn của Python, dùng để tạo ra các chuỗi ID duy nhất (không bao giờ trùng).
# dạng 550e8400-e29b-41d4-a716-446655440000
# 32 ký tự (số + chữ), chia thành 5 nhóm cách nhau bởi dấu -.
import uuid

# thư viện lấy ngày giờ hiện tại, tính toán thời gian,định dạng ngày tháng..
from datetime import datetime 

# Đây là các "loại cột" và "công cụ" để bạn định nghĩa bảng trong database.
# Mỗi cái tương ứng với 1 kiểu dữ liệu trong SQL.
from sqlalchemy import (
   Boolean,
   CheckConstraint, # Ràng buộc điều kiện
   DateTime,
   ForeignKey, # Khóa ngoại (liên kết bảng)
   Integer,
   LargeBinary, # Dữ liệu nhị phân (file, ảnh)
   String,
   Text, # Trong SQL: TEXT — không giới hạn độ dài → Dùng cho: bài viết, mô tả, comment... (dài)
   text, # Cho phép bạn viết SQL trực tiếp khi cần.
)

# Lấy kiểu cột UUID — riêng của PostgreSQ
# tại sao dừng kiểu dữ liệu này mà kh dùng string vì kiểu dữ liệu UUID dùng ít byte hơn string 
# suy ra truy vấn nhanh hơn nữa
from sqlalchemy.dialects.postgresql import UUID 

''' dùng  SQLAlchemy 2.x
2 thứ này dùng để KHAI BÁO CỘT trong bảng.
Mapped[...] = nói "cột này kiểu gì"
mapped_column(...) = nói "cột này cấu hình ra sao
"'''
from sqlalchemy.orm import Mapped, mapped_column

# Lấy class Base từ file app/database/database.py về để dùng.
from app.database.database import Base


class Voter(Base):
    __tablename__ = "voters"

    __table_args__ = (
        CheckConstraint(
            "activated = FALSE OR "
            "(password_hash IS NOT NULL AND public_key IS NOT NULL)",
            name="chk_voter_activated",
        ),
    )

    voter_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    activation_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    activated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    password_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    salt: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    public_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    party: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )


class Vote(Base):
    __tablename__ = "votes"

    __table_args__ = (
        CheckConstraint(
            "octet_length(iv) = 12",
            name="chk_iv_len",
        ),
        CheckConstraint(
            "octet_length(tag) = 16",
            name="chk_tag_len",
        ),
    )

    vote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    ciphertext: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    wrapped_dek: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    iv: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    tag: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )


class VoterStatus(Base):
    __tablename__ = "voter_status"

    __table_args__ = (
        CheckConstraint(
            "has_voted = FALSE OR "
            "(sig_cast IS NOT NULL "
            "AND receipt_hash IS NOT NULL "
            "AND voted_at IS NOT NULL)",
            name="chk_voted_has_proof",
        ),
    )

    voter_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("voters.voter_id"),
        primary_key=True,
    )
    has_voted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    sig_cast: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    receipt_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    voted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class UsedNonce(Base):
    __tablename__ = "used_nonces"

    nonce: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )