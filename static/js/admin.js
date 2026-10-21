/*
MỤC ĐÍCH: Đăng nhập admin và chỉ hiển thị tổng phiếu sau khi bầu cử kết thúc.
PHỤ THUỘC: ui.js, POST /admin/login, GET /results, sessionStorage riêng.
LUỒNG: Lấy JWT admin, gọi results, tạo hàng bằng textContent; lỗi thì ẩn kết quả cũ.
TỰ KIỂM TRA: Trước giờ kết thúc hiện 403; kết quả 0 và lỗi máy chủ có trạng thái khác nhau.
*/

import { apiJson, showStatus } from "./ui.js";

const form = document.querySelector("#admin-form");
const status = document.querySelector("#status");
const refresh = document.querySelector("#refresh");
const logout = document.querySelector("#logout");
const resultSection = document.querySelector("#results");

function setLoggedIn(value) {
  form.hidden = value;
  refresh.hidden = !value;
  logout.hidden = !value;
}

async function loadResults() {
  const token = sessionStorage.getItem("admin_token");
  if (!token) return;
  refresh.disabled = true;
  resultSection.hidden = true;
  showStatus(status, "Đang kiểm phiếu…");
  try {
    const data = await apiJson("/results", { headers: { Authorization: `Bearer ${token}` } });
    const rows = document.querySelector("#result-rows");
    rows.replaceChildren();
    for (const item of data.results) {
      const row = document.createElement("tr");
      for (const value of [item.name, String(item.votes)]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      rows.append(row);
    }
    document.querySelector("#total").textContent = `Tổng số phiếu: ${data.total_votes}`;
    resultSection.hidden = false;
    showStatus(status, "Đã tải tổng kết quả.", "success");
  } catch (error) {
    if (error.status === 401) {
      sessionStorage.removeItem("admin_token");
      setLoggedIn(false);
    }
    showStatus(status, error.status === 403 ? "Cuộc bầu cử chưa kết thúc hoặc tài khoản không có quyền xem kết quả." : error.message, "error");
  } finally {
    refresh.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  showStatus(status, "Đang đăng nhập…");
  try {
    const data = await apiJson("/admin/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: form.elements.username.value, password: form.elements.password.value }),
    });
    sessionStorage.setItem("admin_token", data.access_token);
    form.elements.password.value = "";
    setLoggedIn(true);
    await loadResults();
  } catch (error) {
    showStatus(status, error.message, "error");
  } finally {
    button.disabled = false;
  }
});

refresh.addEventListener("click", loadResults);
logout.addEventListener("click", () => {
  sessionStorage.removeItem("admin_token");
  resultSection.hidden = true;
  setLoggedIn(false);
  showStatus(status, "Đã đăng xuất.");
});

if (sessionStorage.getItem("admin_token")) {
  setLoggedIn(true);
  await loadResults();
}
