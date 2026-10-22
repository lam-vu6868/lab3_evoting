/*
MỤC ĐÍCH: Kích hoạt cử tri và tải bản sao khóa RSA riêng trên thiết bị.
PHỤ THUỘC: crypto.js, ui.js, POST /activate; không gửi private key lên backend.
LUỒNG: Tạo/lấy lại cặp khóa theo voter_id, lưu trước khi gửi, gửi public key rồi báo kết quả.
TỰ KIỂM TRA: Thử kích hoạt bằng DB riêng, tải backup, tải lại trang và thử lại khi lỗi mạng.
*/

import { generateVoterKeys, loadPrivateKey, loadPublicKeyPem, saveVoterKeys } from "./crypto.js";
import { apiJson, downloadPrivateKey, showStatus } from "./ui.js";

const form = document.querySelector("#activate-form");
const status = document.querySelector("#status");
const backup = document.querySelector("#backup");
const continueLink = document.querySelector("#continue");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button[type=submit]");
  const voterId = form.elements.voter_id.value.trim();
  button.disabled = true;
  showStatus(status, "Đang chuẩn bị khóa và gửi yêu cầu…");
  try {
    let publicKey = loadPublicKeyPem(voterId);
    if (!publicKey) {
      if (await loadPrivateKey(voterId)) throw new Error("Đã có khóa riêng nhưng thiếu khóa công khai. Hãy dùng tài khoản đã kích hoạt hoặc liên hệ người quản lý.");
      publicKey = await saveVoterKeys(voterId, await generateVoterKeys());
    } else if (!await loadPrivateKey(voterId)) {
      throw new Error("Thiếu khóa riêng cho khóa công khai đã lưu. Nếu đã kích hoạt, hãy đăng nhập rồi nhập bản sao ở trang bỏ phiếu; nếu chưa, hãy liên hệ người quản lý.");
    }
    backup.hidden = false;
    const result = await apiJson("/activate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voter_id: voterId, activation_code: form.elements.activation_code.value,
        password: form.elements.password.value, public_key: publicKey }),
    });
     if (result.success !== true) throw new Error("Máy chủ chưa xác nhận kích hoạt");
    showStatus(status, "Kích hoạt thành công. Hãy tải bản sao khóa riêng trước khi đăng nhập.", "success");
    continueLink.hidden = false;
    form.elements.activation_code.value = "";
    form.elements.password.value = "";
  } catch (error) {
    showStatus(status, error instanceof TypeError ? "Không liên lạc được máy chủ. Khóa đã lưu trên thiết bị; thử lại với cùng mã cử tri." : error.message, "error");
  } finally {
    button.disabled = false;
  }
});

backup.addEventListener("click", async () => {
  try {
    const voterId = form.elements.voter_id.value.trim();
    await downloadPrivateKey(voterId);
    showStatus(status, "Đã tải file sao lưu. Giữ kín file này.", "success");
  } catch (error) {
    showStatus(status, error.message, "error");
  }
});
