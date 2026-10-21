"""
FILE: app/main.py
TRẠNG THÁI: Đã gắn /activate, /login, /candidates; các route khác chưa triển khai.
MỤC ĐÍCH: Điểm vào FastAPI, chỉ gắn route từ các module theo chức năng.
PHỤ THUỘC: app.auth.activate, app.auth.login, app.api.candidates.
LUỒNG: Tạo app, gắn route kích hoạt, đăng nhập, ứng viên. /vote,
/admin/login và /results sẽ được gắn khi có code và test tương ứng.
TỰ KIỂM TRA: python -m unittest tests.test_activate tests.test_login tests.test_candidates -v.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

from fastapi import FastAPI

from app.auth.activate import router as activate_router
from app.auth.login import router as login_router
from app.api.candidates import router as candidates_router


app = FastAPI()
app.include_router(activate_router)
app.include_router(login_router)
app.include_router(candidates_router)
