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
Đối chiếu từng cột với init.sql; không thay tên cột; thử INSERT phiếu bằng quyền app_user thực.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
