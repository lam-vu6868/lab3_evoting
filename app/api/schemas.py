"""
FILE: app/api/schemas.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Định nghĩa hợp đồng JSON request/response, không truy vấn DB.
PHỤ THUỘC: Pydantic; docs/STRUCTURE.md; không cần import models.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. ActivationRequest: voter_id, activation_code, password, public_key. LoginRequest: voter_id, password.
2. AdminLoginRequest: username, password. TokenResponse: access_token, token_type, election_id cho cử tri.
3. CandidateResponse: candidate_id, name, party. Ballot: candidate_id int dương, nonce, ts int.
4. VoteRequest: ballot, sig_ballot Base64, sig_cast Base64. VoteResponse: success, receipt dạng hex.
5. ResultResponse: results [{candidate_id, name, votes}], total_votes.
6. Cấm extra fields ở payload ký; nonce là 32 ký tự hex chữ thường (16 byte ngẫu nhiên);
   giới hạn độ dài theo SQL; ts strict integer, không nhận float/bool; voter_id và election_id ASCII.
7. Giới hạn kích thước PEM/chữ ký/password hợp lý; PEM và crypto được kiểm tra sâu ở service.
8. Không đưa password_hash, salt, khóa bí mật hoặc ciphertext vào response công khai.

TỰ KIỂM TRA:
Payload thiếu/sai kiểu/quá dài bị từ chối; response không lộ trường DB nhạy cảm.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
