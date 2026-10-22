# 5. Tải danh sách ứng viên

**Ví dụ:** Sau khi `SV001` đăng nhập, trang `/static/vote.html` mở ra và hiển thị ứng viên B có `candidate_id = 2`.

1. `static/js/vote.js` đọc `voter_id`, JWT và `election_id` từ `sessionStorage`. Nếu thiếu, trang chuyển về đăng nhập.
2. Trang gọi `GET /candidates`. `app/api/candidates.py:list_candidates()` dùng session `app_user` đọc bảng `candidates`, sắp theo `candidate_id`.
3. API chỉ trả `candidate_id`, `name`, `party`. JavaScript tạo radio để cử tri chọn; nếu danh sách rỗng, nút gửi phiếu bị vô hiệu hóa. Luồng này không ghi DB.
4. Việc chọn ứng viên B trên trang chưa phải là bỏ phiếu. Chỉ khi bấm **Ký và gửi phiếu**, luồng ở [06-bo-phieu.md](06-bo-phieu.md) mới bắt đầu. Backend sẽ kiểm tra lại `candidate_id = 2` tại thời điểm gửi; dữ liệu hiển thị trên trình duyệt không thay thế kiểm tra server.

**Code:** [vote.js](../static/js/vote.js), [candidates.py](../app/api/candidates.py), [models.py](../app/database/models.py). **Kiểm tra:** [test_candidates.py](../tests/test_candidates.py).
