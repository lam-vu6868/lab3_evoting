/*
MỤC ĐÍCH: Gửi JSON, hiển thị trạng thái và tải file sao lưu khóa riêng trên giao diện.
PHỤ THUỘC: fetch, DOM, crypto.js; không gửi token, mật khẩu hoặc khóa lên máy chủ.
LUỒNG: Gửi request, đọc response JSON, báo lỗi HTTP; trang tự quyết định trạng thái tiếp theo.
TỰ KIỂM TRA: Mở các trang qua /static/ trong browser, thử lỗi API và kiểm nội dung trạng thái.
*/

import { exportPrivateKeyPem, loadPrivateKey } from "./crypto.js";

export async function apiJson(path, options = {}) {
  const response = await fetch(path, options);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`Máy chủ trả dữ liệu không hợp lệ (${response.status})`);
  }
  if (!response.ok) {
    const error = new Error(typeof data.detail === "string" ? data.detail : "Yêu cầu không thành công");
    error.status = response.status;
    throw error;
  }
  return data;
}

export function showStatus(element, message, kind = "info") {
  element.textContent = message;
  element.dataset.kind = kind;
}

export async function downloadPrivateKey(voterId) {
  const key = await loadPrivateKey(voterId);
  if (!key) throw new Error("Không tìm thấy khóa riêng trên thiết bị");
  const url = URL.createObjectURL(new Blob([await exportPrivateKeyPem(key)], { type: "application/x-pem-file" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${voterId}-private.pem`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
