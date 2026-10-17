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
# Path biến chuỗi đường dẫn thành đối tượng có các hàm mkdir(), exists(), read_bytes().
from pathlib import Path

# cryptography là thư viện mật mã đã được ghim trong requirements.txt.
# hashes chứa SHA-256; serialization đọc và ghi khóa theo định dạng PEM.
from cryptography.hazmat.primitives import hashes, serialization
# padding.OAEP định nghĩa cách RSA mã hóa an toàn; rsa tạo và kiểm tra khóa RSA.
from cryptography.hazmat.primitives.asymmetric import padding, rsa


# File này chứa khóa bí mật RSA; chỉ backend kiểm phiếu được phép đọc.
PRIVATE_KEY_FILENAME = "private_key.pem"
# File này chứa khóa công khai RSA; backend dùng nó để bọc DEK khi nhận phiếu.
PUBLIC_KEY_FILENAME = "public_key.pem"
# AES-256 yêu cầu khóa 256 bit; một byte có 8 bit nên 256 / 8 = 32 byte.
DEK_SIZE_BYTES = 32  # AES-256 dùng khóa 256 bit = 32 byte.


class KMS:
    """KMS mô phỏng: giữ cặp RSA local để bảo vệ khóa AES của từng phiếu.

    Đây chưa phải dịch vụ KMS độc lập. Người có quyền đọc thư mục ``key_dir``
    vẫn có thể lấy private key và giải mã các khóa AES đã bọc.
    """

    def __init__(self, key_dir: str | Path):
        """Ghi nhớ nơi chứa khóa; hàm này chưa đọc file và chưa sinh khóa.

        ``self`` là chính đối tượng KMS đang được tạo. ``str | Path`` nghĩa là
        người gọi có thể truyền chuỗi ``"./kms_keys"`` hoặc một đối tượng Path.
        """
        # Chuyển cả str và Path về cùng kiểu Path để các dòng sau xử lý thống nhất.
        self.key_dir = Path(key_dir)
        # Toán tử / của Path ghép thư mục với tên file private key.
        self.private_key_path = self.key_dir / PRIVATE_KEY_FILENAME
        # Tạo đường dẫn public key nằm cùng thư mục nhưng là file riêng.
        self.public_key_path = self.key_dir / PUBLIC_KEY_FILENAME

    def ensure_keys(self) -> None:
        """Tạo cặp RSA lần đầu hoặc kiểm tra và dùng lại private key hiện có.

        ``-> None`` cho biết hàm chỉ chuẩn bị file khóa, không trả kết quả.
        """
        # parents=True tạo cả thư mục cha còn thiếu; exist_ok=True không lỗi nếu đã có.
        self.key_dir.mkdir(parents=True, exist_ok=True)

        # Public key còn mà private key mất thường có nghĩa khóa cũ đã bị xóa.
        # Tạo private key mới lúc này sẽ khiến các phiếu cũ không thể giải mã.
        # exists() chỉ kiểm tra file có tồn tại, chưa đọc nội dung file.
        if self.public_key_path.exists() and not self.private_key_path.exists():
            # RuntimeError buộc startup dừng để quản trị viên phục hồi private key cũ.
            raise RuntimeError(
                "Đã có public key nhưng thiếu private key KMS; "
                "không tự tạo khóa mới để tránh mất khả năng giải mã phiếu cũ"
            )

        # Chỉ sinh cặp khóa mới khi hoàn toàn chưa có private key.
        if not self.private_key_path.exists():
            # generate_private_key tạo khóa bằng bộ sinh số ngẫu nhiên mật mã của hệ thống.
            private_key = rsa.generate_private_key(
                # 65537 là số mũ công khai tiêu chuẩn, cân bằng an toàn và hiệu năng.
                public_exponent=65537,
                # 2048 là số bit của mô-đun RSA theo thiết kế dự án.
                key_size=2048,
            )
            # Chuyển đối tượng private key trong RAM thành bytes để ghi xuống file.
            private_pem = private_key.private_bytes(
                # PEM tạo file văn bản có BEGIN/END và phần giữa mã hóa Base64.
                encoding=serialization.Encoding.PEM,
                # PKCS8 là cấu trúc chuẩn dùng để lưu private key.
                format=serialization.PrivateFormat.PKCS8,
                # Không đặt mật khẩu file; bản demo dựa vào quyền truy cập thư mục.
                encryption_algorithm=serialization.NoEncryption(),
            )

            # try cho phép xử lý riêng trường hợp tiến trình khác vừa tạo file trước.
            try:
                # 0o600 yêu cầu chỉ chủ file được đọc/ghi trên hệ điều hành hỗ trợ
                # quyền kiểu POSIX. O_EXCL làm lệnh lỗi nếu tiến trình khác đã tạo file.
                descriptor = os.open(
                    # Đây là đích duy nhất được phép chứa private key của KMS này.
                    self.private_key_path,
                    # Mở để ghi, tạo mới và từ chối nếu file đã tồn tại.
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    # Trên POSIX: chủ file được đọc/ghi, người khác không có quyền.
                    0o600,
                )
                # fdopen đổi số descriptor thành file Python; "wb" là ghi bytes.
                with os.fdopen(descriptor, "wb") as private_file:
                    # Ghi toàn bộ private key PEM; with tự đóng file sau dòng này.
                    private_file.write(private_pem)
            except FileExistsError:
                # Một tiến trình khác đã thắng cuộc đua tạo khóa. Ta bỏ khóa vừa sinh
                # và nạp file thắng cuộc thay vì ghi đè nó.
                private_key = self._load_private_key()
        else:
            # Trường hợp khởi động lại bình thường: nạp khóa đã dùng cho phiếu cũ.
            private_key = self._load_private_key()

        # Public key không phải bí mật và có thể dựng lại từ private key hợp lệ.
        # Nếu file public bị thiếu, hỏng hoặc không khớp, ghi lại bản đúng.
        # public_key() lấy nửa công khai từ private key đang được xem là nguồn chuẩn.
        expected_public_pem = private_key.public_key().public_bytes(
            # Public key cũng ghi theo vỏ PEM để dễ lưu và tương thích thư viện.
            encoding=serialization.Encoding.PEM,
            # SubjectPublicKeyInfo (SPKI) tạo header "BEGIN PUBLIC KEY" chuẩn.
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        # So sánh public key trên đĩa với public key đúng suy ra từ private key.
        if self._read_public_pem_if_valid() != expected_public_pem:
            # Thiếu, hỏng hoặc không khớp thì thay public key; không thay private key.
            self._replace_public_key_atomically(expected_public_pem)

    def wrap_dek(self, dek: bytes) -> bytes:
        """Mã hóa một khóa AES-256 bằng public key RSA của hệ thống.

        Tham số ``dek`` và kết quả đều là bytes. Kết quả gọi là ``wrapped_dek``.
        """
        # isinstance chặn chuỗi; len chặn khóa AES ngắn hoặc dài hơn 256 bit.
        if not isinstance(dek, bytes) or len(dek) != DEK_SIZE_BYTES:
            # ValueError nói rằng kiểu có thể đúng nhưng giá trị đầu vào không hợp lệ.
            raise ValueError("DEK phải là bytes có đúng 32 byte để dùng AES-256")

        # Bọc khóa chỉ cần public key; private key chưa cần được đưa vào bộ nhớ.
        public_key = self._load_public_key()
        # encrypt trả bytes RSA ciphertext; OAEP quy định cách đệm an toàn trước mã hóa.
        return public_key.encrypt(dek, self._oaep_padding())

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        """Dùng private key RSA mở khóa AES đã được ``wrap_dek`` bảo vệ.

        Chỉ private key cùng cặp với public key đã bọc mới mở được dữ liệu này.
        """
        # RSA decrypt nhận dữ liệu nhị phân; không tự chuyển chuỗi Base64 thành bytes.
        if not isinstance(wrapped_dek, bytes):
            # TypeError dùng khi người gọi truyền sai loại dữ liệu hoàn toàn.
            raise TypeError("wrapped_dek phải là bytes")

        # Chỉ nạp private key đúng lúc cần mở DEK.
        private_key = self._load_private_key()
        # decrypt đảo phép RSA-OAEP; sai khóa hoặc dữ liệu hỏng sẽ phát sinh ValueError.
        dek = private_key.decrypt(wrapped_dek, self._oaep_padding())
        # Kiểm tra phòng thủ: hệ thống chỉ chấp nhận DEK dành cho AES-256.
        if len(dek) != DEK_SIZE_BYTES:
            raise ValueError("Khóa sau khi mở không có đúng 32 byte")
        # Trả DEK nguyên bản cho crypto_service dùng giải mã ciphertext của phiếu.
        return dek

    # staticmethod dùng vì hàm không đọc hoặc sửa thuộc tính nào trong self.
    @staticmethod
    def _oaep_padding() -> padding.OAEP:
        """Dùng đúng giao thức RSA-OAEP SHA-256 đã chốt trong STRUCTURE.md."""
        # Tạo mới cấu hình padding để cả wrap và unwrap luôn dùng cùng tham số.
        return padding.OAEP(
            # MGF1 tạo mặt nạ trong OAEP; dự án quy định nó dùng SHA-256.
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            # SHA-256 này là hàm băm chính của OAEP.
            algorithm=hashes.SHA256(),
            # label=None nghĩa là không gắn nhãn phụ; hai phía phải dùng cùng giá trị.
            label=None,
        )

    def _load_private_key(self) -> rsa.RSAPrivateKey:
        """Đọc và kiểm tra private key KMS từ PEM; không giữ khóa trong thuộc tính."""
        # try gom lỗi đọc file và lỗi định dạng thành một thông báo của ứng dụng.
        try:
            # load_pem_private_key phân tích bytes PEM thành đối tượng khóa sử dụng được.
            private_key = serialization.load_pem_private_key(
                # read_bytes đọc toàn bộ file mà không biến dữ liệu thành chuỗi Unicode.
                self.private_key_path.read_bytes(),
                # File được ghi bằng NoEncryption nên không có mật khẩu để mở.
                password=None,
            )
        except (OSError, ValueError, TypeError) as error:
            # from error giữ nguyên nguyên nhân kỹ thuật để debug nội bộ khi cần.
            raise RuntimeError("Private key KMS bị thiếu hoặc không hợp lệ") from error

        # Hàm loader có thể đọc nhiều loại khóa, nên cần xác nhận đây thật sự là RSA.
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise RuntimeError("Private key KMS phải là khóa RSA")
        # Không nhận khóa RSA kích thước khác với hợp đồng 2048 bit của hệ thống.
        if private_key.key_size != 2048:
            raise RuntimeError("Private key KMS phải có kích thước 2048 bit")
        # Kiểu đã được kiểm tra; caller có thể gọi decrypt() an toàn về mặt giao diện.
        return private_key

    def _load_public_key(self) -> rsa.RSAPublicKey:
        """Đọc public key PEM dùng để bọc DEK."""
        # try chuyển các lỗi file/PEM thành lỗi có ý nghĩa trong ngữ cảnh KMS.
        try:
            # load_pem_public_key phân tích SPKI PEM thành đối tượng public key.
            public_key = serialization.load_pem_public_key(
                # Public key cũng được đọc dạng bytes để serialization xử lý trực tiếp.
                self.public_key_path.read_bytes()
            )
        except (OSError, ValueError) as error:
            # Không in nội dung khóa trong thông báo lỗi để tránh lộ dữ liệu mật mã.
            raise RuntimeError("Public key KMS bị thiếu hoặc không hợp lệ") from error

        # Loader hỗ trợ nhiều thuật toán nên phải loại EC/DSA và chỉ nhận RSA.
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise RuntimeError("Public key KMS phải là khóa RSA")
        # Public key cũng phải đúng kích thước 2048 bit như private key nguồn.
        if public_key.key_size != 2048:
            raise RuntimeError("Public key KMS phải có kích thước 2048 bit")
        # Trả đối tượng có phương thức encrypt() cho wrap_dek.
        return public_key

    def _read_public_pem_if_valid(self) -> bytes | None:
        """Trả PEM chuẩn nếu public key đọc được; lỗi thì để ensure_keys phục hồi.

        ``bytes | None`` nghĩa là thành công trả bytes, còn lỗi trả ``None``.
        """
        # Gọi lại một nơi kiểm tra loại RSA và kích thước thay vì lặp logic.
        try:
            public_key = self._load_public_key()
        except RuntimeError:
            # None là tín hiệu cho ensure_keys rằng public key cần được tạo lại.
            return None
        # Chuẩn hóa khóa đã đọc về đúng PEM/SPKI trước khi so sánh bytes.
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def _replace_public_key_atomically(self, public_pem: bytes) -> None:
        """Ghi đủ file tạm rồi mới thay public key bằng một thao tác nguyên tử."""
        # Ban đầu chưa có file tạm; kiểu | None cho phép biểu diễn trạng thái này.
        temporary_path: Path | None = None
        # finally bên dưới luôn dọn file tạm dù ghi file hoặc replace phát sinh lỗi.
        try:
            # NamedTemporaryFile tạo tên không trùng trong chính thư mục KMS.
            with tempfile.NamedTemporaryFile(
                # "wb" mở file để ghi dữ liệu bytes của PEM.
                mode="wb",
                # Cùng thư mục giúp os.replace hoạt động trong một filesystem.
                dir=self.key_dir,
                # Prefix giúp quản trị viên nhận biết file tạm nếu tiến trình bị dừng.
                prefix="public_key_",
                # Suffix phân biệt file tạm với hai file PEM chính thức.
                suffix=".tmp",
                # Giữ file sau khi đóng để os.replace có thể sử dụng đường dẫn.
                delete=False,
            ) as temporary_file:
                # Ghi đầy đủ public key trước khi thay file chính thức.
                temporary_file.write(public_pem)
                # Lưu tên file dạng Path để dùng sau khi khối with đã đóng file.
                temporary_path = Path(temporary_file.name)
            # Thay file đích trong một thao tác, tránh public_key.pem chỉ có nửa nội dung.
            os.replace(temporary_path, self.public_key_path)
        finally:
            # Nếu ghi hoặc replace lỗi, xóa file tạm; missing_ok tránh lỗi khi replace
            # đã thành công và đường dẫn tạm không còn tồn tại.
            if temporary_path is not None:
                # missing_ok=True không báo lỗi nếu os.replace đã chuyển file thành công.
                temporary_path.unlink(missing_ok=True)
