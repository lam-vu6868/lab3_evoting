"""
MỤC ĐÍCH: POST /admin/login cấp JWT quản trị viên từ tài khoản trong cấu hình.
PHỤ THUỘC: AdminLoginRequest/AdminTokenResponse, auth.py; không truy vấn bảng voters.
LUỒNG: So sánh username/password với cấu hình; sai trả lỗi chung, đúng cấp JWT role admin.
TỰ KIỂM TRA: python -m unittest tests.test_tally -v.
"""

from fastapi import APIRouter, HTTPException

from app.api.schemas import AdminLoginRequest, AdminTokenResponse
from app.auth.auth import create_jwt, verify_admin_credentials


router = APIRouter()


@router.post("/admin/login", response_model=AdminTokenResponse)
async def admin_login(request: AdminLoginRequest) -> AdminTokenResponse:
    if not verify_admin_credentials(request.username, request.password):
        raise HTTPException(401, "Thông tin đăng nhập không hợp lệ")
    return AdminTokenResponse(access_token=create_jwt(request.username, "admin"))
