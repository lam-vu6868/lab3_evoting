"""
FILE: app/crypto/kms.py
TRẠNG THÁI: Đã triển khai tạo/nạp khóa RSA và bọc/mở khóa AES.
MỤC ĐÍCH: Quản lý cặp RSA của hệ thống để bọc/mở khóa AES; khác khóa ký của cử tri.
PHỤ THUỘC: app/core/config.py; cryptography; thư mục KMS_KEY_DIR (local: ./kms_keys).

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Tạo KMS(key_dir), ensure_keys(), wrap_dek(dek: bytes), unwrap_dek(wrapped: bytes).
2. ensure_keys chạy rõ ràng lúc startup: nếu chưa có cặp khóa thì sinh RSA 2048, exponent 65537.
3. Lưu PEM: private ở file riêng với quyền hạn chế, public ở file riêng.
   Tạo file an toàn/atomic; tránh hai tiến trình sinh hai cặp. Nếu thiếu/hỏng một file,
   báo lỗi hoặc khôi phục public từ private hợp lệ; không âm thầm thay private cũ.
4. wrap_dek chỉ cần public key; dùng OAEP với SHA-256, MGF1 SHA-256, label=None.
5. unwrap_dek chỉ nạp private khi cần; trả đúng 32 byte khóa AES hoặc báo lỗi.
6. Không có endpoint xuất khóa. Private vẫn được lưu trên volume, không phải chỉ tồn tại trong RAM.
7. Không coi class này là KMS độc lập: người kiểm soát backend/thư mục khóa vẫn có thể lấy khóa.

TỰ KIỂM TRA:
Wrap rồi unwrap khớp; restart dùng lại khóa; private sai không mở được; mất khóa không được tự thay để tiếp tục kiểm phiếu.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
"""

# os cung cấp thao tác tạo file độc quyền. Nhờ O_EXCL, hai tiến trình cùng
# khởi động không thể âm thầm ghi đè private key của nhau.
import os
# tempfile tạo file tạm ngay trong thư mục khóa trước khi thay public key.
# Cách này tránh để lại public key mới chỉ được ghi một phần nếu máy dừng giữa chừng.
import tempfile
from pathlib import Path

# cryptography là thư viện mật mã đã được ghim trong requirements.txt.
# hashes chứa SHA-256; serialization đọc và ghi khóa theo định dạng PEM.
from cryptography.hazmat.primitives import hashes, serialization
# padding.OAEP định nghĩa cách RSA mã hóa an toàn; rsa tạo và kiểm tra khóa RSA.
from cryptography.hazmat.primitives.asymmetric import padding, rsa


# Tên file cố định giúp mọi lần khởi động tìm lại đúng một cặp khóa hệ thống.
PRIVATE_KEY_FILENAME = "private_key.pem"
PUBLIC_KEY_FILENAME = "public_key.pem"
DEK_SIZE_BYTES = 32  # AES-256 dùng khóa 256 bit = 32 byte.


class KMS:
    """KMS mô phỏng: giữ cặp RSA local để bảo vệ khóa AES của từng phiếu.

    Đây chưa phải dịch vụ KMS độc lập. Người có quyền đọc thư mục ``key_dir``
    vẫn có thể lấy private key và giải mã các khóa AES đã bọc.
    """

    def __init__(self, key_dir: str | Path):
        # Path giúp ghép đường dẫn bằng toán tử / và đọc/ghi file dạng bytes.
        self.key_dir = Path(key_dir)
        self.private_key_path = self.key_dir / PRIVATE_KEY_FILENAME
        self.public_key_path = self.key_dir / PUBLIC_KEY_FILENAME

    def ensure_keys(self) -> None:
        """Tạo cặp RSA lần đầu hoặc kiểm tra và dùng lại private key hiện có."""
        self.key_dir.mkdir(parents=True, exist_ok=True)

        # Public key còn mà private key mất thường có nghĩa khóa cũ đã bị xóa.
        # Tạo private key mới lúc này sẽ khiến các phiếu cũ không thể giải mã.
        if self.public_key_path.exists() and not self.private_key_path.exists():
            raise RuntimeError(
                "Đã có public key nhưng thiếu private key KMS; "
                "không tự tạo khóa mới để tránh mất khả năng giải mã phiếu cũ"
            )

        if not self.private_key_path.exists():
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            try:
                # 0o600 yêu cầu chỉ chủ file được đọc/ghi trên hệ điều hành hỗ trợ
                # quyền kiểu POSIX. O_EXCL làm lệnh lỗi nếu tiến trình khác đã tạo file.
                descriptor = os.open(
                    self.private_key_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(descriptor, "wb") as private_file:
                    private_file.write(private_pem)
            except FileExistsError:
                # Một tiến trình khác đã thắng cuộc đua tạo khóa. Ta bỏ khóa vừa sinh
                # và nạp file thắng cuộc thay vì ghi đè nó.
                private_key = self._load_private_key()
        else:
            private_key = self._load_private_key()

        # Public key không phải bí mật và có thể dựng lại từ private key hợp lệ.
        # Nếu file public bị thiếu, hỏng hoặc không khớp, ghi lại bản đúng.
        expected_public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        if self._read_public_pem_if_valid() != expected_public_pem:
            self._replace_public_key_atomically(expected_public_pem)

    def wrap_dek(self, dek: bytes) -> bytes:
        """Mã hóa một khóa AES-256 bằng public key RSA của hệ thống."""
        if not isinstance(dek, bytes) or len(dek) != DEK_SIZE_BYTES:
            raise ValueError("DEK phải là bytes có đúng 32 byte để dùng AES-256")

        public_key = self._load_public_key()
        return public_key.encrypt(dek, self._oaep_padding())

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        """Dùng private key RSA mở khóa AES đã được ``wrap_dek`` bảo vệ."""
        if not isinstance(wrapped_dek, bytes):
            raise TypeError("wrapped_dek phải là bytes")

        private_key = self._load_private_key()
        dek = private_key.decrypt(wrapped_dek, self._oaep_padding())
        if len(dek) != DEK_SIZE_BYTES:
            raise ValueError("Khóa sau khi mở không có đúng 32 byte")
        return dek

    @staticmethod
    def _oaep_padding() -> padding.OAEP:
        """Dùng đúng giao thức RSA-OAEP SHA-256 đã chốt trong STRUCTURE.md."""
        return padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        )

    def _load_private_key(self) -> rsa.RSAPrivateKey:
        """Đọc và kiểm tra private key KMS từ PEM; không giữ khóa trong thuộc tính."""
        try:
            private_key = serialization.load_pem_private_key(
                self.private_key_path.read_bytes(),
                password=None,
            )
        except (OSError, ValueError, TypeError) as error:
            raise RuntimeError("Private key KMS bị thiếu hoặc không hợp lệ") from error

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise RuntimeError("Private key KMS phải là khóa RSA")
        if private_key.key_size != 2048:
            raise RuntimeError("Private key KMS phải có kích thước 2048 bit")
        return private_key

    def _load_public_key(self) -> rsa.RSAPublicKey:
        """Đọc public key PEM dùng để bọc DEK."""
        try:
            public_key = serialization.load_pem_public_key(
                self.public_key_path.read_bytes()
            )
        except (OSError, ValueError) as error:
            raise RuntimeError("Public key KMS bị thiếu hoặc không hợp lệ") from error

        if not isinstance(public_key, rsa.RSAPublicKey):
            raise RuntimeError("Public key KMS phải là khóa RSA")
        if public_key.key_size != 2048:
            raise RuntimeError("Public key KMS phải có kích thước 2048 bit")
        return public_key

    def _read_public_pem_if_valid(self) -> bytes | None:
        """Trả PEM chuẩn nếu public key đọc được; lỗi thì để ensure_keys phục hồi."""
        try:
            public_key = self._load_public_key()
        except RuntimeError:
            return None
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def _replace_public_key_atomically(self, public_pem: bytes) -> None:
        """Ghi đủ file tạm rồi mới thay public key bằng một thao tác nguyên tử."""
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.key_dir,
                prefix="public_key_",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_file.write(public_pem)
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, self.public_key_path)
        finally:
            # Nếu ghi hoặc replace lỗi, xóa file tạm; missing_ok tránh lỗi khi replace
            # đã thành công và đường dẫn tạm không còn tồn tại.
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
