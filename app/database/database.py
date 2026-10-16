"""
FILE: app/database/database.py
TRẠNG THÁI: Đã tạo ba AsyncEngine, ba AsyncSession factory và dependency get_db().
MỤC ĐÍCH: Tạo ba kết nối PostgreSQL async theo ba role, quản lý vòng đời session.
PHỤ THUỘC: app/core/config.py; SQLAlchemy asyncio; asyncpg; db/init.sql.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Khai báo Base (DeclarativeBase), ba AsyncEngine từ ba DATABASE_URL riêng.
2. Tạo AppSession, AdminSession, TallySession bằng async_sessionmaker; không dùng postgres.
3. get_db() async yield AppSession và đóng bằng async context manager; không tự commit.
4. Tally nhận TallySession qua caller; không dùng AppSession đọc votes.
5. Quyền sở hữu transaction: caller mở async with session.begin() trước truy vấn;
   voting_service không tự begin một transaction đã được SQLAlchemy autobegin.
6. Không Base.metadata.create_all() bằng app_user; schema do SQL init tạo.
7. Tắt echo SQL để tránh log payload; không in connection string có mật khẩu.

TỰ KIỂM TRA:
AsyncSession đóng kể cả khi lỗi; app_user INSERT votes nhưng không SELECT; tally_user chỉ đọc.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
# AsyncGenerator mô tả hàm async có yield như get_db().
from collections.abc import AsyncGenerator

# DeclarativeBase là lớp gốc cho các model ở models.py.
from sqlalchemy.orm import DeclarativeBase

# AsyncSession đại diện một phiên làm việc async với DB.
# async_sessionmaker tạo session; create_async_engine quản lý kết nối asyncpg.
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# lấy các biến môi trường  
from app.core.config import get_settings


settings = get_settings()
# Base là lớp cha chung để SQLAlchemy quản lý metadata của các model.
class Base(DeclarativeBase):
    pass 

# Mỗi engine(kết nối) dùng một DB role riêng; echo=False để không log nội dung SQL.
app_engine = create_async_engine(settings.APP_DATABASE_URL, echo=False) # echo in log cú pháp truy vấn ra terminel
admin_engine = create_async_engine(settings.ADMIN_DATABASE_URL, echo=False)
tally_engine = create_async_engine(settings.TALLY_DATABASE_URL, echo=False)

# Factory tạo AsyncSession tương ứng với từng role.
# expire_on_commit=False : mục đích để sau khi commit không xóa object để return chả dữ liệu về cho lớp ui/ux
# vì mình dùng async nên phải để false vì nếu gọi lại sau khi commit thì sẽ phải đợi await nhưng await kh dc tự gọi 
# dùng Sync  thì kh cần await nên nó tự gọi lại chỉ thêm 1 query nx thôi    
AppSession = async_sessionmaker(app_engine, expire_on_commit=False) 
AdminSession = async_sessionmaker(admin_engine, expire_on_commit=False)
TallySession = async_sessionmaker(tally_engine, expire_on_commit=False)



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Cấp AppSession cho FastAPI và luôn đóng session sau request."""
    async with AppSession() as session: # Tạo ra 1 session mới, đặt tên nó là session, dùng xong tự đóng.
        yield session





 
