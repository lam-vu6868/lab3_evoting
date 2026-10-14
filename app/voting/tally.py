"""
FILE: app/voting/tally.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Đọc và giải mã phiếu trong bộ nhớ, trả tổng sau khi cuộc bầu cử kết thúc.
PHỤ THUỘC: TallySession; models; crypto_service.decrypt_vote; config thời gian.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. tally_votes(session, settings, kms) kiểm tra now >= ELECTION_END ngay trong service.
2. Đọc candidates và votes bằng tally_user; tạo bộ đếm 0 cho mọi ứng viên.
3. Xáo trộn danh sách phiếu của demo trong RAM, không coi xáo trộn là bảo đảm ẩn danh.
4. Mỗi phiếu: unwrap wrapped_dek, decrypt ciphertext/iv/tag, parse envelope có giới hạn.
5. Đọc ballot.candidate_id, kiểm tra thuộc danh sách, tăng bộ đếm.
6. Phiếu lỗi tag/JSON/ứng viên: dừng trả kết quả và báo lỗi kiểm phiếu tổng quát;
   không âm thầm bỏ qua rồi trình bày tổng thiếu như kết quả hợp lệ.
7. Trả results và total_votes; không trả từng phiếu/khóa, không ghi kết quả hoặc plaintext vào DB.
8. Không SELECT voters để thử ghép chữ ký với người bầu; role tally không có quyền này.
9. Tránh log plaintext; không hứa del sẽ xóa sạch bộ nhớ Python.

TỰ KIỂM TRA:
Trước giờ kết thúc bị chặn; bảng rỗng trả các ứng viên 0 phiếu; dữ liệu lỗi không cho kết quả âm thầm sai.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
