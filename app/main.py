"""
FILE: app/main.py
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Điểm vào FastAPI và 6 route HTTP; gọi service, không nhét thuật toán mã hóa vào route.
PHỤ THUỘC: app.core.config, app.database.database, app.database.models,
app.api.schemas, app.auth.auth, app.crypto.kms,
app.voting.voting_service, app.voting.tally.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo app=FastAPI(); lifespan khởi tạo KMS rõ ràng; mount /static bằng đường dẫn từ __file__.
2. POST /activate: mở session.begin() trước query; khóa dòng voters bằng FOR UPDATE;
   kiểm tra chưa activated, mã kích hoạt và public key; hash password; UPDATE voters
   (activation_hash=NULL, activated=true, password_hash, salt, public_key), INSERT voter_status.
3. POST /login: đọc voters, kiểm tra activated/password; trả JWT và election_id. Không ghi DB.
4. GET /candidates: đọc candidate_id/name/party bằng app_user.
5. POST /vote: require_voter chỉ đọc JWT; with session.begin(): gọi cast_vote(...).
   Sau khi context commit thành công mới return. Bắt lỗi bên ngoài context để rollback đầy đủ.
6. POST /admin/login: đối chiếu cấu hình, cấp token role=admin.
7. GET /results: require_admin, mở TallySession, gọi tally_votes; đóng session kể cả khi lỗi.
8. Quy ước lỗi: 401 sai đăng nhập/token; 403 sai quyền/chưa cho kiểm phiếu;
   409 bầu lại/nonce trùng; 400 yêu cầu nghiệp vụ sai; 422 schema sai; 500 lỗi kiểm phiếu.
9. Chỉ ánh xạ unique violation đúng constraint thành 409; lỗi DB khác không giả là trùng nonce.
10. Không tạo /decrypt hoặc /private-key. Route /register cũ được thay bằng /activate;
    tên trang register.html vẫn giữ để tránh đổi liên kết.

TỰ KIỂM TRA:
Sau khi tự triển khai, /docs có 6 route; response không lộ exception SQL/secret; token voter không gọi results được.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
