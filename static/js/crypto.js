/*
FILE: static/js/crypto.js
TRẠNG THÁI: Đã triển khai helper, kiểm tra trong browser; chưa nối giao diện.
MỤC ĐÍCH: Các helper WebCrypto dùng chung cho trang kích hoạt và bỏ phiếu.
PHỤ THUỘC: Web Crypto API, TextEncoder, btoa/atob, localStorage của browser;
           hợp đồng byte với app/crypto/signature_service.py; không cần thư viện ngoài.

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

// crypto.subtle là Web Crypto API có sẵn trong browser; không cần thư viện ngoài.
// RSA-PSS là khóa ký của cử tri, khác RSA-OAEP của KMS dùng để bọc khóa AES.
export async function generateVoterKeys() {
  return crypto.subtle.generateKey(
    { name: "RSA-PSS", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, // Cho phép xuất PKCS8 để cử tri sao lưu; đồng thời tăng rủi ro nếu có XSS.
    ["sign", "verify"],
  );
}

// btoa/atob chỉ nhận byte nhị phân, nên chuyển từng byte của ArrayBuffer sang ký tự.
function bytesToBase64(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)));
}

function base64ToBytes(base64) {
  if (typeof base64 !== "string" || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(base64)) {
    throw new Error("Dữ liệu Base64 không hợp lệ");
  }
  const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
  if (bytesToBase64(bytes) !== base64) throw new Error("Dữ liệu Base64 không chuẩn");
  return bytes;
}

function toPem(label, bytes) {
  const base64 = bytesToBase64(bytes);
  const lines = base64.match(/.{1,64}/g).join("\n");
  return `-----BEGIN ${label}-----\n${lines}\n-----END ${label}-----\n`;
}

// SPKI là định dạng public key mà Python load_voter_public_key() chấp nhận.
export async function exportPublicKeyPem(publicKey) {
  return toPem("PUBLIC KEY", await crypto.subtle.exportKey("spki", publicKey));
}

// PKCS8 chứa private key: chỉ đưa cho cử tri giữ, không gửi tới backend hay ghi log.
export async function exportPrivateKeyPem(privateKey) {
  return toPem("PRIVATE KEY", await crypto.subtle.exportKey("pkcs8", privateKey));
}

export async function importPrivateKeyPem(pem) {
  const match = typeof pem === "string" && pem.match(/^-----BEGIN PRIVATE KEY-----\r?\n((?:[A-Za-z0-9+/=]+\r?\n)+)-----END PRIVATE KEY-----\s*$/);
  if (!match) {
    throw new Error("Private key phải là PKCS8 PEM");
  }
  const base64 = match[1].replace(/\r?\n/g, "");
  const key = await crypto.subtle.importKey(
    "pkcs8", base64ToBytes(base64), { name: "RSA-PSS", hash: "SHA-256" }, true, ["sign"],
  );
  if (key.algorithm.modulusLength !== 2048 ||
      bytesToBase64(key.algorithm.publicExponent) !== "AQAB") {
    throw new Error("Private key phải là RSA 2048 với exponent 65537");
  }
  return key;
}

// Chỉ chấp nhận hai payload phẳng trong STRUCTURE.md; không ký object tùy ý.
export function canonicalBytes(payload) {
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("Payload phải là object JSON");
  }
  const keys = Object.keys(payload).sort();
  const ballot = keys.join(",") === "candidate_id,nonce,ts";
  const cast = keys.join(",") === "election_id,nonce,ts,voter_id";
  if (!ballot && !cast) throw new Error("Payload phải có đúng các trường của ballot hoặc cast");
  if (ballot && (!Number.isSafeInteger(payload.candidate_id) || payload.candidate_id <= 0)) {
    throw new Error("candidate_id phải là số nguyên dương an toàn");
  }
  if (cast && (
    typeof payload.election_id !== "string" || payload.election_id.length < 1 ||
    payload.election_id.length > 100 || !/^[\x20-\x7e]+$/.test(payload.election_id) ||
    typeof payload.voter_id !== "string" || !/^[A-Za-z0-9_-]{1,20}$/.test(payload.voter_id)
  )) throw new Error("election_id hoặc voter_id không hợp lệ");
  if (typeof payload.nonce !== "string" || !/^[0-9a-f]{32}$/.test(payload.nonce)) {
    throw new Error("nonce phải là 32 ký tự hex chữ thường");
  }
  if (!Number.isSafeInteger(payload.ts)) throw new Error("ts phải là số nguyên an toàn");

  // JSON.stringify giữ thứ tự khóa của object mới; TextEncoder đổi chuỗi thành UTF-8.
  return new TextEncoder().encode(JSON.stringify(Object.fromEntries(keys.map((key) => [key, payload[key]]))));
}

export async function signPayload(privateKey, payload) {
  // saltLength=32 byte phải khớp RSA-PSS SHA-256 trong signature_service.py.
  const signature = await crypto.subtle.sign(
    { name: "RSA-PSS", saltLength: 32 }, privateKey, canonicalBytes(payload),
  );
  return bytesToBase64(signature); // Base64 chuẩn để gửi qua JSON HTTP.
}

export function randomNonce() {
  // getRandomValues dùng nguồn ngẫu nhiên mật mã của browser: 16 byte = 32 ký tự hex.
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, "0")).join("");
}

function storageKey(voterId) {
  if (typeof voterId !== "string" || !/^[A-Za-z0-9_-]{1,20}$/.test(voterId)) {
    throw new Error("voter_id không hợp lệ");
  }
  return `voter_private_key:${voterId}`;
}

export async function savePrivateKey(voterId, privateKey) {
  // localStorage giữ PKCS8 Base64 qua lần đóng browser; chỉ dùng cho bản demo.
  const pkcs8 = await crypto.subtle.exportKey("pkcs8", privateKey);
  localStorage.setItem(storageKey(voterId), bytesToBase64(pkcs8));
}

export async function loadPrivateKey(voterId) {
  const stored = localStorage.getItem(storageKey(voterId));
  if (stored === null) return null;
  // Nạp và kiểm tra định dạng thật; dữ liệu hỏng phải báo lỗi, không tạo khóa mới.
  return importPrivateKeyPem(toPem("PRIVATE KEY", base64ToBytes(stored)));
}
