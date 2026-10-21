"""
FILE: app/auth/auth.py
TRẠNG THÁI: Đã có hash/verify mật khẩu, mã kích hoạt, JWT, Bearer theo role và đối chiếu admin.
MỤC ĐÍCH: Băm mật khẩu, kiểm tra mã kích hoạt, cấp/xác minh JWT và đối chiếu admin.
PHỤ THUỘC: app/core/config.py; cryptography PBKDF2HMAC; hashlib/hmac của Python;
           python-jose cho JWT; FastAPI cho Bearer dependency; không sinh khóa RSA.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Chốt PBKDF2-HMAC-SHA256 để tận dụng dependency hiện có và cột salt riêng.
   hash_password(password) trả (encoded_hash_bytes, salt_bytes); salt ngẫu nhiên cho từng tài khoản.
2. encoded_hash lưu phiên bản + iterations + digest; verify_password đọc tham số đã lưu,
   không lệ thuộc iterations cấu hình mới; so sánh constant-time. Hiệu chỉnh iterations trước sử dụng thật.
3. Mã kích hoạt sẽ do seed sinh đủ ngẫu nhiên: hash_activation_code lưu SHA-256(code)
   trong activation_hash; verify_activation_code so sánh hash an toàn;
   không áp dụng SHA-256 đơn thuần cho mật khẩu người dùng.
4. create_jwt(subject, role) dùng secret riêng, thuật toán cố định HS256, sub/role/iat/exp.
5. verify_jwt bắt buộc exp, sub, role hợp lệ; allowlist HS256, không lấy thuật toán từ request.
6. Dependency lấy Bearer token; require_voter/require_admin kiểm tra đúng role.
7. Admin đối chiếu cấu hình bằng so sánh hằng thời gian; không lưu admin vào voters.
8. Route /login đọc voters: activated=true rồi verify password. Sai trả lỗi chung, không log mật khẩu.

TỰ KIỂM TRA:
Cùng mật khẩu có salt khác; mã kích hoạt sai, JWT sửa/hết hạn/sai role đều bị từ chối.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

import hashlib  # SHA-256 tạo digest 32 byte của mã kích hoạt ngẫu nhiên.
import hmac  # compare_digest so sánh hash mà không dừng sớm theo nội dung.
import os  # os.urandom lấy salt ngẫu nhiên từ hệ điều hành.
from time import time  # Unix seconds cho hai claim iat và exp trong JWT.

from cryptography.exceptions import InvalidKey  # verify() báo mật khẩu sai bằng lỗi này.
from cryptography.hazmat.primitives import hashes  # SHA-256 dùng bên trong PBKDF2-HMAC.
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # python-jose ký và kiểm tra JWT bằng HS256.

from app.core.config import PBKDF2_MAX_ITERATIONS, get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> tuple[bytes, bytes]:
    """Tạo password_hash tự mô tả và salt riêng để lưu ở hai cột voters."""
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ValueError("Mật khẩu phải là chuỗi dài từ 8 đến 128 ký tự")
    try:
        password_bytes = password.encode("utf-8")
    except UnicodeError as error:
        raise ValueError("Mật khẩu phải mã hóa được UTF-8") from error

    iterations = get_settings().PBKDF2_ITERATIONS
    salt = os.urandom(16)  # Mỗi tài khoản có salt khác nhau; salt không cần giữ bí mật.
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    digest = kdf.derive(password_bytes)
    # Lưu thuật toán và số vòng lặp cùng digest để lần đăng nhập sau đọc lại đúng tham số.
    encoded_hash = (
        b"pbkdf2_sha256$" + str(iterations).encode("ascii")
        + b"$" + digest.hex().encode("ascii")
    )
    return encoded_hash, salt


def verify_password(password: str, encoded_hash: bytes, salt: bytes) -> bool:
    """Kiểm tra mật khẩu với tham số trong hash đã lưu, không dùng cấu hình hiện tại."""
    if (
        not isinstance(password, str) or not 1 <= len(password) <= 128
        or not isinstance(encoded_hash, bytes) or not isinstance(salt, bytes) or len(salt) < 16
    ):
        return False
    try:
        password_bytes = password.encode("utf-8")
    except UnicodeError:
        return False

    parts = encoded_hash.split(b"$")
    if (len(parts) != 3 or parts[0] != b"pbkdf2_sha256"
            or not parts[1].isdigit() or len(parts[1]) > 8):
        return False
    iterations = int(parts[1])
    if not 1 <= iterations <= PBKDF2_MAX_ITERATIONS or len(parts[2]) != 64:
        return False
    try:
        digest = bytes.fromhex(parts[2].decode("ascii"))
    except (UnicodeError, ValueError):
        return False

    # PBKDF2HMAC.verify tự so sánh digest an toàn; không dùng toán tử == cho dữ liệu mật mã.
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    try:
        kdf.verify(password_bytes, digest)
    except InvalidKey:
        return False
    return True


def hash_activation_code(code: str) -> bytes:
    """Băm mã kích hoạt ngẫu nhiên để lưu ở voters.activation_hash."""
    if not isinstance(code, str) or not 1 <= len(code) <= 256:
        raise ValueError("Mã kích hoạt phải là chuỗi dài từ 1 đến 256 ký tự")
    try:
        code_bytes = code.encode("utf-8")
    except UnicodeError as error:
        raise ValueError("Mã kích hoạt phải mã hóa được UTF-8") from error
    # Chỉ dùng SHA-256 trực tiếp vì seed sẽ sinh mã ngẫu nhiên dài; mật khẩu dùng PBKDF2.
    return hashlib.sha256(code_bytes).digest()


def verify_activation_code(code: str, stored_hash: bytes) -> bool:
    """Trả True khi mã nhập khớp hash trong DB; dữ liệu sai trả False."""
    if not isinstance(stored_hash, bytes) or len(stored_hash) != 32:
        return False
    try:
        actual_hash = hash_activation_code(code)
    except ValueError:
        return False
    return hmac.compare_digest(actual_hash, stored_hash)


def create_jwt(subject: str, role: str) -> str:
    """Ký JWT chứa danh tính, role và thời gian hết hạn bằng secret của backend."""
    if not isinstance(subject, str) or not 1 <= len(subject) <= 100 or not subject.strip():
        raise ValueError("Chủ thể JWT không hợp lệ")
    if role not in ("voter", "admin"):
        raise ValueError("Role JWT không hợp lệ")

    settings = get_settings()
    issued_at = int(time())
    claims = {
        "sub": subject,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + settings.JWT_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")


def verify_jwt(token: str) -> dict[str, str | int]:
    """Xác minh chữ ký và claim JWT; token sai gây ValueError chung."""
    if not isinstance(token, str) or not 1 <= len(token) <= 4096:
        raise ValueError("JWT không hợp lệ")
    try:
        claims = jwt.decode(
            token,
            get_settings().JWT_SECRET,
            algorithms=["HS256"],  # Không chọn thuật toán từ header do người gửi kiểm soát.
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except JWTError as error:
        raise ValueError("JWT không hợp lệ") from error

    now = int(time())
    if (
        not isinstance(claims.get("sub"), str)
        or not 1 <= len(claims["sub"]) <= 100
        or not claims["sub"].strip()
        or claims.get("role") not in ("voter", "admin")
        or type(claims.get("iat")) is not int
        or type(claims.get("exp")) is not int
        or claims["iat"] > now
        or claims["exp"] <= now
        or claims["exp"] <= claims["iat"]
    ):
        raise ValueError("JWT không hợp lệ")
    return claims


def _require_role(credentials: HTTPAuthorizationCredentials | None, role: str) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Token không hợp lệ", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = verify_jwt(credentials.credentials)
    except ValueError as error:
        raise HTTPException(401, "Token không hợp lệ", headers={"WWW-Authenticate": "Bearer"}) from error
    if claims["role"] != role:
        raise HTTPException(403, "Không đủ quyền")
    return claims["sub"]


def require_voter(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    """Lấy voter_id từ Bearer JWT hợp lệ có role voter; không truy vấn DB."""
    return _require_role(credentials, "voter")


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    """Lấy subject từ Bearer JWT hợp lệ có role admin; không truy vấn DB."""
    return _require_role(credentials, "admin")


def verify_admin_credentials(username: str, password: str) -> bool:
    """Đối chiếu tài khoản admin với cấu hình; không đọc bảng voters."""
    if (not isinstance(username, str) or not 1 <= len(username) <= 100
            or not isinstance(password, str) or not 1 <= len(password) <= 128):
        return False

    settings = get_settings()
    try:
        username_bytes = username.encode("utf-8")
        password_bytes = password.encode("utf-8")
        configured_username = settings.ADMIN_USERNAME.encode("utf-8")
        configured_password = settings.ADMIN_PASSWORD.encode("utf-8")
    except UnicodeError:
        return False

    username_matches = hmac.compare_digest(username_bytes, configured_username)
    password_matches = hmac.compare_digest(password_bytes, configured_password)
    return username_matches and password_matches
