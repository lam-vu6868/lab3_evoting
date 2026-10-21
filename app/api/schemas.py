"""
FILE: app/api/schemas.py
TRẠNG THÁI: Đã triển khai đủ schema request/response của thiết kế hiện tại.
MỤC ĐÍCH: Định nghĩa hợp đồng JSON request/response, không truy vấn DB.
PHỤ THUỘC: Pydantic; docs/STRUCTURE.md; không cần import models.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. ActivationRequest: voter_id, activation_code, password, public_key. LoginRequest: voter_id, password.
2. AdminLoginRequest: username, password. TokenResponse có election_id cho cử tri;
   AdminTokenResponse chỉ có access_token và token_type.
3. CandidateResponse: candidate_id, name, party. Ballot: candidate_id int dương, nonce, ts int.
4. VoteRequest: ballot, sig_ballot Base64, sig_cast Base64. VoteResponse: success, receipt dạng hex.
5. ResultResponse: results [{candidate_id, name, votes}], total_votes.
6. Cấm extra fields ở payload ký; nonce là 32 ký tự hex chữ thường (16 byte ngẫu nhiên);
   giới hạn độ dài theo SQL; ts strict integer, không nhận float/bool; voter_id và election_id ASCII.
7. Giới hạn kích thước PEM/chữ ký/password hợp lý; PEM và crypto được kiểm tra sâu ở service.
8. Không đưa password_hash, salt, khóa bí mật hoặc ciphertext vào response công khai.

TỰ KIỂM TRA:
Payload thiếu/sai kiểu/quá dài bị từ chối; response không lộ trường DB nhạy cảm.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""


# base64 giải mã chuỗi chữ ký nhận từ JSON để kiểm tra định dạng.
import base64
# binascii cung cấp lỗi khi chuỗi không đúng định dạng Base64.
import binascii
# Literal giới hạn một field chỉ nhận đúng giá trị đã khai báo.
from typing import Literal

# BaseModel là lớp cha giúp schema tự kiểm tra dữ liệu.
# ConfigDict cấu hình chung cho toàn bộ schema.
# Field thêm giới hạn độ dài, giá trị và biểu thức chính quy.
# StrictInt chỉ nhận số nguyên thật, không tự đổi True hoặc chuỗi thành số.
# field_validator chạy hàm kiểm tra riêng cho một hoặc nhiều field.
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

# ================== 1. Schema dùng chung + kích hoạt/đăng nhập=======================
class ApiSchema(BaseModel):
   """Schema API mặc định từ chối các trường không được khai báo.
      vd: mình chỉ cho 2 trường là tên và full name nhưng client gửi field  lạ như
        voter_id="V001",
        full_name="An",
        is_admin=True,     # ← field lạ
   """
   # extra="forbid" từ chối mọi field không được khai báo trong schema.
   model_config= ConfigDict(extra="forbid")


class ActivationRequest(ApiSchema):
   """Dữ liệu cử tri gửi để kích hoạt tài khoản lần đầu."""

   # voter_id là mã cử tri đã có sẵn trong bảng voters.
   voter_id: str = Field(
      min_length=1,  # Không nhận chuỗi rỗng.
      max_length=20,  # Khớp cột voters.voter_id VARCHAR(20).
      pattern=r"^[A-Za-z0-9_-]+$",  # Chỉ nhận chữ ASCII, số, _ và -.
   )

   # activation_code là mã bí mật dùng một lần để kích hoạt tài khoản.
   activation_code: str = Field(
      min_length=1,  # Không nhận mã rỗng.
      max_length=256,  # Chặn request có mã quá lớn.
   )
   # password phải đủ dài nhưng không được làm request phình quá mức.
   password: str = Field(min_length=8, max_length=128)
   # public_key là khóa công khai PEM; private key không được gửi lên server.
   public_key: str = Field(min_length=1, max_length=8192)


class LoginRequest(ApiSchema):
   """Dữ liệu cử tri gửi để đăng nhập."""

   # voter_id xác định tài khoản cử tri cần đăng nhập.
   voter_id: str = Field(
      min_length=1,  # Không nhận chuỗi rỗng.
      max_length=20,  # Khớp cột voters.voter_id VARCHAR(20).
      pattern=r"^[A-Za-z0-9_-]+$",  # Chỉ nhận chữ ASCII, số, _ và -.
   )
   # password được route /login kiểm tra với password_hash trong database.
   password: str = Field(min_length=1, max_length=128)


class AdminLoginRequest(ApiSchema):
   """Dữ liệu quản trị viên gửi để đăng nhập."""

   # username được so sánh với ADMIN_USERNAME trong cấu hình.
   username: str = Field(min_length=1, max_length=100)
   # password được so sánh với ADMIN_PASSWORD trong cấu hình.
   password: str = Field(min_length=1, max_length=128)


# ====================== 2. Ứng viên + lá phiếu =====================
class TokenResponse(ApiSchema):
   """Token xác thực trả về sau khi cử tri đăng nhập thành công."""

   # access_token là JWT dùng trong header Authorization của request sau.
   access_token: str = Field(min_length=1, max_length=4096)
   # token_type cố định là bearer theo cách FastAPI nhận Bearer token.
   token_type: Literal["bearer"] = "bearer"
   # election_id giúp trình duyệt ký đúng mã cuộc bầu cử hiện tại.
   election_id: str = Field(
      min_length=1,  # Không nhận mã cuộc bầu cử rỗng.
      max_length=100,  # Giới hạn kích thước dữ liệu trả về.
      pattern=r"^[\x20-\x7E]+$",  # Chỉ nhận ký tự ASCII nhìn thấy được.
   )


class AdminTokenResponse(ApiSchema):
   """JWT của quản trị viên; không trả mã cuộc bầu cử hay thông tin tài khoản."""

   access_token: str = Field(min_length=1, max_length=4096)
   token_type: Literal["bearer"] = "bearer"


class CandidateResponse(ApiSchema):
   """Thông tin một ứng viên trả cho trình duyệt hiển thị."""

   # candidate_id là khóa chính dương của ứng viên.
   candidate_id: int = Field(gt=0)
   # name khớp cột candidates.name VARCHAR(100).
   name: str = Field(min_length=1, max_length=100)
   # party có thể là None vì cột candidates.party cho phép NULL.
   party: str | None = Field(default=None, max_length=50)


class Ballot(ApiSchema):
   """Lựa chọn ứng viên cùng dữ liệu chống phát lại và chống sửa."""

   # candidate_id dùng StrictInt để từ chối True, số thực và chuỗi số.
   candidate_id: StrictInt = Field(gt=0)
   # nonce là 16 byte ngẫu nhiên được biểu diễn bằng 32 ký tự hex thường.
   nonce: str = Field(pattern=r"^[0-9a-f]{32}$")
   # ts là Unix timestamp; StrictInt từ chối số thực và giá trị bool.
   ts: StrictInt

# ====================== 3. Gửi phiếu + phản hồi =====================
class VoteRequest(ApiSchema):
   """Dữ liệu trình duyệt gửi khi cử tri bỏ phiếu."""

   # ballot chứa ứng viên, nonce chống phát lại và thời điểm ký.
   ballot: Ballot
   # sig_ballot là chữ ký Base64 của nội dung ballot.
   sig_ballot: str = Field(min_length=1, max_length=1024)
   # sig_cast là chữ ký Base64 xác nhận hành động bỏ phiếu.
   sig_cast: str = Field(min_length=1, max_length=1024)

   # Dùng cùng một hàm để kiểm tra cả hai trường chữ ký.
   @field_validator("sig_ballot", "sig_cast")
   @classmethod
   def validate_base64_signature(cls, value: str) -> str:
      """Từ chối chữ ký không phải chuỗi Base64 chuẩn."""

      try:
         # validate=True từ chối ký tự lạ và padding Base64 sai.
         base64.b64decode(value, validate=True)
      except (ValueError, binascii.Error):
         # Pydantic chuyển ValueError thành lỗi validation của field.
         raise ValueError("Chữ ký phải là Base64 hợp lệ") from None

      # Giữ nguyên chuỗi để service kiểm tra chữ ký RSA ở bước sau.
      return value


class VoteResponse(ApiSchema):
   """Kết quả trả về sau khi transaction bỏ phiếu đã commit."""

   # Endpoint thành công chỉ trả giá trị True.
   success: Literal[True] = True
   # receipt là SHA-256 dạng 64 ký tự hex thường.
   receipt: str = Field(pattern=r"^[0-9a-f]{64}$")

# ====================== 4. Kết quả kiểm phiếu ======================
class ResultItem(ApiSchema):
   """Kết quả đếm phiếu của một ứng viên."""

   # candidate_id xác định ứng viên; phải là số nguyên dương.
   candidate_id: StrictInt = Field(gt=0)
   # name là tên ứng viên hiển thị cho quản trị viên.
   name: str = Field(min_length=1, max_length=100)
   # votes là số phiếu nhận được; có thể bằng 0 nhưng không được âm.
   votes: StrictInt = Field(ge=0)


class ResultResponse(ApiSchema):
   """Tổng kết quả kiểm phiếu sau khi cuộc bầu cử kết thúc."""

   # results chứa kết quả của từng ứng viên.
   results: list[ResultItem]
   # total_votes là tổng số phiếu hợp lệ đã đếm.
   total_votes: StrictInt = Field(ge=0)
