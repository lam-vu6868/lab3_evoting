"""
FILE: app/core/config.py
TRẠNG THÁI: Đã đọc cấu hình và kiểm tra mã cuộc bầu cử, thời gian, tham số dương.
MỤC ĐÍCH: Đọc cấu hình một lần, cung cấp Settings cho các module.
PHỤ THUỘC: .env hoặc biến môi trường máy chạy backend; pydantic-settings.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo Settings và get_settings(); đọc .env khi chạy local, ưu tiên biến môi trường.
   Hiện chỉ PostgreSQL ở Docker: 3 DB URL dùng 127.0.0.1:5433/evoting;
   KMS_KEY_DIR dùng ./kms_keys. Docker Compose không truyền config cho backend local.
2. Khai báo JWT_SECRET, APP_DATABASE_URL, ADMIN_DATABASE_URL, TALLY_DATABASE_URL,
   ADMIN_USERNAME, ADMIN_PASSWORD, KMS_KEY_DIR, ELECTION_ID, ELECTION_START, ELECTION_END.
3. Thêm tham số JWT hết hạn, PBKDF2 iterations, cửa sổ request 300 giây.
4. Parse thời gian có múi giờ; yêu cầu START < END; ELECTION_ID không rỗng.
5. Báo thiếu cấu hình bằng tên trường, không in secret/URL có mật khẩu.
6. Không tạo kết nối DB và không sinh khóa trong module cấu hình.

TỰ KIỂM TRA:
Cấu hình thiếu phải lỗi rõ; thời gian thiếu múi giờ phải bị từ chối; secret không xuất hiện trong log.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""
from datetime import datetime  # Kiểu dữ liệu ngày giờ.
# BaseSettings:
# - Dùng để tạo class cấu hình
# - Tự đọc biến môi trường
# - Tự kiểm tra kiểu dữ liệu
# - Tự ép kiểu nếu có thể
#
# SettingsConfigDict:
# - Dùng để cấu hình cho BaseSettings
# - Ví dụ: đọc file .env, encoding, có phân biệt hoa thường hay không...
from pydantic_settings import BaseSettings, SettingsConfigDict

# Lưu lại cấu hình sau lần đọc đầu để các lần gọi sau dùng lại.
from functools import lru_cache

# field_validator và model_validator thuộc thư viện Pydantic,
# dùng để kiểm tra dữ liệu trước khi chấp nhận tạo object.
from pydantic import Field, field_validator, model_validator
# field_validator dùng để kiểm tra một field cụ thể.
# Còn model_validator dùng khi bạn cần kiểm tra nhiều field với nhau.


class Settings(BaseSettings):
    """
    Class Settings dùng để gom toàn bộ cấu hình của project vào một nơi.

    Vì Settings kế thừa BaseSettings nên khi tạo:

        settings = Settings()

    Pydantic sẽ tự tìm các biến môi trường tương ứng
    rồi gán vào các thuộc tính bên dưới.
    """
    # Đọc file .env khi chạy từ thư mục gốc dự án.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    # Xác thực đăng nhập. gt=0 nghĩa là giá trị phải lớn hơn 0.
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = Field(default=60, gt=0)

    # Kết nối database theo từng quyền
    APP_DATABASE_URL: str
    ADMIN_DATABASE_URL: str
    TALLY_DATABASE_URL: str

    # Tài khoản admin của ứng dụng
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Nơi lưu khóa KMS
    KMS_KEY_DIR: str = "./kms_keys"

    # Thông tin cuộc bầu cử
    ELECTION_ID: str
    ELECTION_START: datetime
    ELECTION_END: datetime

    # Tham số dùng ở các bước sau
    VOTE_REQUEST_MAX_AGE_SECONDS: int = Field(default=300, gt=0)  # 5 phút
    PBKDF2_ITERATIONS: int = Field(default=600000, gt=0)  # 600.000 vòng

    # Kiểm tra đầu vào
    @field_validator("ELECTION_ID")
    @classmethod
    def validate_election_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("ELECTION_ID không được để trống")
        return value

    @model_validator(mode="after")
    def validate_election_time(self) -> "Settings":
        # Kiểm tra múi giờ trước khi so sánh để tránh TypeError.
        if (self.ELECTION_START.utcoffset() is None or self.ELECTION_END.utcoffset() is None):
            raise ValueError(
                "ELECTION_START và ELECTION_END phải có múi giờ"
            )

        if self.ELECTION_START >= self.ELECTION_END:
            raise ValueError(
                "ELECTION_START phải nhỏ hơn ELECTION_END"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
