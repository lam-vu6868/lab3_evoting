/*
MỤC ĐÍCH: Đăng nhập cử tri và giữ JWT/election_id trong phiên tab.
PHỤ THUỘC: POST /login, sessionStorage; không lưu mật khẩu hay tạo khóa.
LUỒNG: Gửi form, lưu token cùng voter_id và election_id, chuyển sang vote.html.
TỰ KIỂM TRA: Mật khẩu sai không chuyển trang; sessionStorage không có password.
*/

import { apiJson, showStatus } from "./ui.js";

const form = document.querySelector("#login-form");
const status = document.querySelector("#status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  showStatus(status, "Đang đăng nhập…");
  try {
    const voterId = form.elements.voter_id.value.trim();
    const data = await apiJson("/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voter_id: voterId, password: form.elements.password.value }),
    });
    sessionStorage.setItem("voter_token", data.access_token);
    sessionStorage.setItem("voter_id", voterId);
    sessionStorage.setItem("election_id", data.election_id);
    form.elements.password.value = "";
    location.assign("/static/vote.html");
  } catch (error) {
    showStatus(status, error instanceof TypeError ? "Không liên lạc được máy chủ" : error.message, "error");
  } finally {
    button.disabled = false;
  }
});
