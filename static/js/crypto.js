/*
FILE: static/js/crypto.js
TRẠNG THÁI: KHUNG HƯỚNG DẪN — chưa có xử lý nghiệp vụ.
MỤC ĐÍCH: Các helper WebCrypto dùng chung cho trang kích hoạt và bỏ phiếu.
PHỤ THUỘC: Web Crypto API của browser; hợp đồng byte với app/crypto/signature_service.py.

CÁCH TRIỂN KHAI THEO THỨ TỰ:
1. Export generateVoterKeys(): RSA-PSS 2048, exponent [1,0,1], SHA-256;
   extractable=true để demo có backup; giải thích rủi ro khóa xuất được.
2. exportPublicKeyPem dùng SPKI; export/import private dùng PKCS8. Không nhầm với RSA KMS/OAEP.
3. canonicalBytes(payload): sắp xếp khóa cấp ngoài, JSON.stringify, TextEncoder UTF-8;
   chỉ nhận payload phẳng đúng schema. Trường ID ASCII, ts int an toàn; không ký object tùy ý.
4. signPayload(privateKey,payload): RSA-PSS saltLength=32, trả Base64 chuẩn.
5. randomNonce(): crypto.getRandomValues 16 byte, chuyển hex chữ thường 32 ký tự.
6. Helper save/load private key theo voter_id (demo localStorage với PKCS8 Base64);
   không gửi lên server, không xóa khi logout. Storage này không bảo vệ khỏi XSS.
7. Helper backup/import có kiểm tra định dạng; không import thành công giả khi khóa lỗi.
8. Không chứa fetch/DOM; trang HTML chịu trách nhiệm giao diện. WebCrypto cần secure context.

TỰ KIỂM TRA:
Ký cùng payload được Python verify; đổi trường bị từ chối; round-trip export/import vẫn ký được.

ĐỌC KÈM: docs/STRUCTURE.md và ROADMAP.md.
*/
