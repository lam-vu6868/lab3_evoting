"""
FILE: app/voting/voting_service.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Điều phối một lần bỏ phiếu và ba thay đổi DB trong cùng transaction.
PHỤ THUỘC: models; signature_service; crypto_service; caller cấp AsyncSession trong transaction.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. async cast_vote(session, voter_id, request, settings, kms) trả receipt; không commit trong hàm.
2. Kiểm tra thời gian bầu cử và |now - ts| <= 300 giây; dùng UTC có timezone.
3. Đọc voter activated/public_key và candidate; lấy voter_id từ JWT đã xác minh, không tin body.
4. Dựng lại ballot/cast bằng ELECTION_ID từ config; verify cả sig_ballot và sig_cast.
5. SELECT VoterStatus WHERE voter_id=... FOR UPDATE; thiếu dòng là lỗi dữ liệu,
   has_voted=true thì từ chối. Khóa phải được giữ đến commit/rollback.
6. INSERT used_nonces(nonce); PK trùng gây lỗi transaction; không SELECT rồi mới INSERT.
7. envelope={ballot, sig_ballot dạng Base64}; serialize UTF-8, encrypt_vote lấy 4 trường bytes.
8. UUID v4 sinh ở Python; Core INSERT votes inline để không RETURNING.
9. SHA-256 trên bytes sig_cast đã decode tạo receipt_hash. UPDATE voter_status:
   has_voted=true, sig_cast bytes, receipt_hash bytes, voted_at làm tròn theo giờ UTC.
10. Trả receipt hex. Caller chỉ gửi success sau khi thoát async session.begin() và commit thành công.
11. Không lưu voter_id/nonce riêng/timestamp ở votes; không sao chép receipt sang votes.
12. Ném lỗi nghiệp vụ riêng; để lỗi DB thoát transaction rồi main mới chuyển thành HTTP.

TỰ KIỂM TRA:
Bầu một lần tăng votes 1; hai request đồng thời chỉ một thành công; lỗi giữa chừng rollback cả ba bảng.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
