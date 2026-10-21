"""
FILE: app/main.py
TRẠNG THÁI: Đã gắn /activate, /login, /candidates, /vote, /admin/login và /results.
MỤC ĐÍCH: Điểm vào FastAPI, chỉ gắn route từ các module theo chức năng.
PHỤ THUỘC: các router đã triển khai, KMS và ba AsyncEngine.
LUỒNG: Khi startup nạp KMS; gắn route kích hoạt, đăng nhập, ứng viên, bỏ phiếu và kiểm phiếu;
khi shutdown đóng engine.
TỰ KIỂM TRA: python -m unittest tests.test_activate tests.test_login tests.test_candidates -v;
STAGE5_TEST_DB_NAME=... python -m unittest tests.test_voting -v.
STAGE6_TEST_DB_NAME=... python -m unittest tests.test_tally -v.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.activate import router as activate_router
from app.auth.login import router as login_router
from app.auth.admin import router as admin_router
from app.api.candidates import router as candidates_router
from app.core.config import get_settings
from app.crypto.kms import KMS
from app.database.database import admin_engine, app_engine, tally_engine
from app.voting.vote import router as vote_router
from app.voting.results import router as results_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Nạp lại khóa KMS hiện có; đóng ba pool DB khi ứng dụng dừng."""
    kms = KMS(get_settings().KMS_KEY_DIR)
    kms.ensure_keys()
    app.state.kms = kms
    try:
        yield
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
        await tally_engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(activate_router)
app.include_router(login_router)
app.include_router(candidates_router)
app.include_router(vote_router)
app.include_router(admin_router)
app.include_router(results_router)
