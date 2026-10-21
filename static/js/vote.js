/*
MỤC ĐÍCH: Hiển thị ứng viên, ký ballot/cast và gửi một phiếu bằng JWT cử tri.
PHỤ THUỘC: crypto.js, ui.js, GET /candidates, POST /vote và token phiên từ login.
LUỒNG: Tải ứng viên, đọc khóa riêng đúng voter_id, ký hai payload, chờ API commit rồi hiện receipt.
TỰ KIỂM TRA: Bầu B trên DB riêng, bầu lại nhận 409; lỗi mạng báo trạng thái chưa chắc chắn.
*/

import { importPrivateKeyPem, loadPrivateKey, randomNonce, savePrivateKey, signPayload } from "./crypto.js";
import { apiJson, downloadPrivateKey, showStatus } from "./ui.js";

const voterId = sessionStorage.getItem("voter_id");
const token = sessionStorage.getItem("voter_token");
const electionId = sessionStorage.getItem("election_id");
const status = document.querySelector("#status");
const form = document.querySelector("#vote-form");
const submit = document.querySelector("#submit-vote");

if (!voterId || !token || !electionId) {
  location.replace("/static/login.html");
} else {
  document.querySelector("#identity").textContent = `Mã cử tri: ${voterId}`;
  try {
    const candidates = await apiJson("/candidates");
    const fieldset = document.querySelector("#candidates");
    for (const candidate of candidates) {
      const label = document.createElement("label");
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "candidate_id";
      radio.value = String(candidate.candidate_id);
      radio.required = true;
      label.append(radio, document.createTextNode(`${candidate.name}${candidate.party ? ` — ${candidate.party}` : ""}`));
      fieldset.append(label);
    }
    submit.disabled = candidates.length === 0;
    showStatus(status, candidates.length ? "Chọn ứng viên rồi ký và gửi phiếu." : "Chưa có ứng viên để chọn.");
  } catch (error) {
    showStatus(status, error.message, "error");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submit.disabled = true;
  showStatus(status, "Đang ký và gửi phiếu…");
  try {
    const key = await loadPrivateKey(voterId);
    if (!key) throw new Error("Thiếu khóa riêng. Hãy nhập file sao lưu bên dưới.");
    const ballot = { candidate_id: Number(form.elements.candidate_id.value), nonce: randomNonce(),
      ts: Math.floor(Date.now() / 1000) };
    const cast = { election_id: electionId, voter_id: voterId, nonce: ballot.nonce, ts: ballot.ts };
    const result = await apiJson("/vote", {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ ballot, sig_ballot: await signPayload(key, ballot),
        sig_cast: await signPayload(key, cast) }),
    });
    if (result.success !== true) throw new Error("Máy chủ chưa xác nhận phiếu");
    document.querySelector("#receipt").textContent = `Biên nhận lần gửi thành công: ${result.receipt}`;
    document.querySelector("#receipt").hidden = false;
    showStatus(status, "Phiếu đã được ghi thành công. Hãy giữ biên nhận.", "success");
  } catch (error) {
    if (error.status === 401) {
      sessionStorage.removeItem("voter_token");
      showStatus(status, "Phiên đăng nhập hết hạn. Hãy đăng nhập lại.", "error");
    } else if (error instanceof TypeError) {
      showStatus(status, "Mất kết nối. Phiếu có thể đã được ghi; hãy kiểm tra trước khi thử lại.", "warning");
    } else {
      showStatus(status, error.message, "error");
    }
  } finally {
    submit.disabled = false;
  }
});

document.querySelector("#import-key").addEventListener("click", async () => {
  try {
    const file = document.querySelector("#private-file").files[0];
    if (!file) throw new Error("Hãy chọn file khóa riêng");
    if (await loadPrivateKey(voterId)) throw new Error("Thiết bị đã có khóa riêng cho cử tri này; không tự ghi đè");
    await savePrivateKey(voterId, await importPrivateKeyPem(await file.text()));
    showStatus(status, "Đã nhập khóa riêng cho mã cử tri hiện tại.", "success");
  } catch (error) {
    showStatus(status, error.message, "error");
  }
});

document.querySelector("#backup-key").addEventListener("click", async () => {
  try {
    await downloadPrivateKey(voterId);
    showStatus(status, "Đã tải file sao lưu. Giữ kín file này.", "success");
  } catch (error) {
    showStatus(status, error.message, "error");
  }
});

document.querySelector("#logout").addEventListener("click", () => {
  for (const key of ["voter_token", "voter_id", "election_id"]) sessionStorage.removeItem(key);
  location.assign("/static/login.html");
});
