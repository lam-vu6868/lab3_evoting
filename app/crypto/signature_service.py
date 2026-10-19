"""
FILE: app/crypto/signature_service.py
TRẠNG THÁI: Đã triển khai chuẩn hóa JSON và kiểm tra chữ ký Python; chưa kiểm tra WebCrypto.
MỤC ĐÍCH: Chuẩn hóa thông điệp và xác minh chữ ký cử tri; backend không giữ private key cử tri.
PHỤ THUỘC: cryptography; giao ước với static/js/crypto.js; không phụ thuộc DB.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo canonical_bytes(payload): JSON khóa sắp xếp tăng dần, không khoảng trắng, UTF-8.
   Payload phẳng, chỉ trường đã quy định; ts là số nguyên an toàn cho JavaScript.
2. build_ballot(candidate_id, nonce, ts) và build_cast(election_id, voter_id, nonce, ts).
3. load_voter_public_key(pem): nhận SPKI PEM PUBLIC KEY; kiểm tra RSA 2048.
4. verify_signature(public_key, payload, signature_bytes): RSA-PSS, SHA-256,
   MGF1 SHA-256, salt_length=32. JS phải dùng đúng saltLength=32.
5. Chữ ký truyền HTTP bằng Base64 chuẩn, decode chặt chẽ trước verify.
6. Tách hàm thuần khỏi HTTPException; trả kết quả/lỗi để main chuyển thành HTTP.
7. Sinh key/sign trong Python chỉ dùng cho test; khóa cử tri thật sinh trong browser.

TỰ KIỂM TRA:
JS và Python tạo cùng byte JSON; chữ ký JS được Python chấp nhận; đổi candidate/nonce/ts hoặc public key thì verify thất bại.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

# Thư viện chuẩn: Base64 để nhận chữ ký HTTP, JSON để tạo cùng bytes với browser.
import base64 # decode chữ ký Base64 từ HTTP
import binascii # bắt lỗi Base64 (binascii.Error)
import json  # tạo canonical JSON bytes
import re # regex kiểm tra nonce, voter_id

# cryptography đọc public key và kiểm tra chữ ký RSA-PSS; backend không ký thay cử tri.
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


MAX_SAFE_INTEGER = 2**53 - 1  # Giới hạn số nguyên mà JavaScript biểu diễn chính xác.
NONCE_PATTERN = re.compile(r"[0-9a-f]{32}")
VOTER_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,20}")


# _check_nonce_and_ts() — kiểm tra ts không vượt ngưỡng.
def _check_nonce_and_ts(nonce: str, ts: int) -> None:
    if not isinstance(nonce, str) or NONCE_PATTERN.fullmatch(nonce) is None:
        raise ValueError("nonce phải là 32 ký tự hex chữ thường")
    if type(ts) is not int or abs(ts) > MAX_SAFE_INTEGER:
        raise ValueError("ts phải là số nguyên an toàn cho JavaScript")


# Tạo payload ballot — dict 3 trường — sau khi validate. Đây là cấu trúc chuẩn mà cử tri ký khi chọn ứng viên.
def build_ballot(candidate_id: int, nonce: str, ts: int) -> dict[str, int | str]:
    """Tạo đúng ba trường mà cử tri ký cho lựa chọn ứng viên."""
    if type(candidate_id) is not int or candidate_id <= 0:
        raise ValueError("candidate_id phải là số nguyên dương")
    _check_nonce_and_ts(nonce, ts)
    return {"candidate_id": candidate_id, "nonce": nonce, "ts": ts}


def build_cast(election_id: str, voter_id: str, nonce: str, ts: int) -> dict[str, int | str]:
    """Tạo đúng bốn trường mà cử tri ký để xác nhận hành động bỏ phiếu."""
    if (
        not isinstance(election_id, str)
        or not 1 <= len(election_id) <= 100
        or any(not " " <= char <= "~" for char in election_id)
    ):
        raise ValueError("election_id phải là ASCII nhìn thấy được")
    if not isinstance(voter_id, str) or VOTER_ID_PATTERN.fullmatch(voter_id) is None:
        raise ValueError("voter_id không hợp lệ")
    _check_nonce_and_ts(nonce, ts)
    return {"election_id": election_id, "voter_id": voter_id, "nonce": nonce, "ts": ts}


def canonical_bytes(payload: dict[str, int | str]) -> bytes:
    """Sắp xếp khóa JSON, bỏ khoảng trắng rồi mã hóa UTF-8 để ký/kiểm tra."""
    if not isinstance(payload, dict):
        raise ValueError("payload phải là object JSON")
    if set(payload) == {"candidate_id", "nonce", "ts"}:
        checked = build_ballot(payload["candidate_id"], payload["nonce"], payload["ts"])
    elif set(payload) == {"election_id", "voter_id", "nonce", "ts"}:
        checked = build_cast(
            payload["election_id"], payload["voter_id"], payload["nonce"], payload["ts"]
        )
    else:
        raise ValueError("payload phải có đúng các trường của ballot hoặc cast")
    return json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def load_voter_public_key(pem: str) -> rsa.RSAPublicKey:
    """Chỉ nhận public key SPKI PEM RSA 2048 của cử tri."""
    if not isinstance(pem, str) or not pem.strip().startswith("-----BEGIN PUBLIC KEY-----"):
        raise ValueError("public key phải là SPKI PEM")
    if not pem.strip().endswith("-----END PUBLIC KEY-----"):
        raise ValueError("public key phải là SPKI PEM")
    try:
        public_key = serialization.load_pem_public_key(pem.encode("ascii"))
    except (UnicodeEncodeError, ValueError) as error:
        raise ValueError("public key không hợp lệ") from error
    if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size != 2048:
        raise ValueError("public key phải là RSA 2048")
    return public_key


def decode_signature(encoded: str) -> bytes:
    """Giải mã Base64 chuẩn; RSA 2048 tạo chữ ký dài đúng 256 byte."""
    if not isinstance(encoded, str):
        raise ValueError("chữ ký phải là Base64")
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("chữ ký phải là Base64 hợp lệ") from error
    if len(signature) != 256 or base64.b64encode(signature).decode("ascii") != encoded:
        raise ValueError("chữ ký phải là Base64 chuẩn của RSA 2048")
    return signature


def verify_signature(
    public_key: rsa.RSAPublicKey, payload: dict[str, int | str], signature_bytes: bytes
) -> bool:
    """Trả True khi chữ ký khớp dữ liệu; chữ ký sai trả False."""
    if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size != 2048:
        raise ValueError("public key phải là RSA 2048")
    if not isinstance(signature_bytes, bytes):
        raise TypeError("chữ ký phải là bytes")
    message = canonical_bytes(payload)
    if len(signature_bytes) != 256:
        return False
    try:
        # SHA-256, MGF1 và salt 32 byte phải khớp WebCrypto ở browser.
        public_key.verify(
            signature_bytes,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return False
    return True
