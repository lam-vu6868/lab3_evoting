"""
FILE: tests/test_attack.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Test API và quyền DB trên môi trường thử nghiệm riêng.
PHỤ THUỘC: unittest; backend đã chạy; PostgreSQL test riêng; có thể dùng urllib.request stdlib.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Yêu cầu URL và DB test riêng, không reset dữ liệu bầu cử thật. Tạo cử tri test/mã kích hoạt có kiểm soát.
2. Test activate một lần, login sai/SQL injection, JWT voter gọi results, chữ ký sai.
3. Replay nguyên request; request quá cũ/tương lai quá 300s; ngoài giờ bầu; tally trước kết thúc.
4. Kết nối bằng admin_app SELECT votes phải permission denied; tally_user UPDATE cũng bị chặn.
5. Nếu chưa cấu hình môi trường, skip với lý do rõ; không báo test đã pass khi chưa chạy.
6. Chạy python -m unittest tests.test_attack; đóng mọi kết nối sau test.

TỰ KIỂM TRA:
Mỗi lỗi bị từ chối đúng loại và không làm thay đổi số phiếu; không in mật khẩu/secret vào output.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
