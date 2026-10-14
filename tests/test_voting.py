"""
FILE: tests/test_voting.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Test transaction và hai yêu cầu bỏ phiếu đồng thời bằng PostgreSQL thật.
PHỤ THUỘC: unittest; database test riêng; voting_service và models sau khi triển khai.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Fixture cử tri đã kích hoạt, voter_status false, ứng viên có sẵn.
2. Bầu hợp lệ: votes +1, nonce +1, trạng thái true, receipt đúng SHA-256(signature bytes).
3. Hai session/kết nối độc lập gửi cùng cử tri đồng thời; chỉ một transaction thành công.
4. Gây lỗi sau INSERT votes trước UPDATE status; kiểm tra rollback votes, nonce và trạng thái.
5. Hai cử tri dùng nonce trùng: transaction thứ hai rollback toàn bộ.
6. Dùng app_user thật kiểm tra INSERT không ngầm RETURNING; không dùng SQLite để kết luận FOR UPDATE đúng.
7. Kiểm tra kích hoạt đồng thời không tạo hai trạng thái hoặc thay public key đã kích hoạt.

TỰ KIỂM TRA:
Kiểm tra DB sau commit/rollback bằng kết nối test được cấp quyền; cleanup chỉ môi trường test riêng.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
