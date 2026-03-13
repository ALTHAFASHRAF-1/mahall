// 1) Put your Render backend URL here after deployment:
const API_BASE = "https://mahall-yzi3.onrender.com"; // <-- CHANGE THIS

const $ = (s) => document.querySelector(s);

function setStatus(msg, kind="") {
  const el = $("#status");
  el.className = "status" + (kind ? " " + kind : "");
  el.textContent = msg;
}

function makeTablesMobileFriendly(container) {
  // Adds data-label attributes so CSS stacked view shows labels
  container.querySelectorAll("table").forEach((table) => {
    const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
    table.querySelectorAll("tbody tr").forEach((tr) => {
      Array.from(tr.children).forEach((td, idx) => {
        td.setAttribute("data-label", headers[idx] || `Col ${idx+1}`);
        // Wrap value for stacked mode
        if (!td.querySelector("span")) {
          const span = document.createElement("span");
          span.textContent = td.textContent;
          td.textContent = "";
          td.appendChild(span);
        }
      });
    });
  });
}

let lastHTML = "";

$("#convertForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = $("#pdfUrl").value.trim();
  const flavor = $("#flavor").value;

  $("#submitBtn").disabled = true;
  $("#copyBtn").disabled = true;
  $("#result").innerHTML = "";
  lastHTML = "";

  try {
    setStatus("Converting… please wait.");

    const res = await fetch(`${API_BASE}/api/convert`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ url, flavor })
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Request failed: ${res.status}`);
    }

    const html = await res.text();
    lastHTML = html;

    $("#result").innerHTML = html;
    makeTablesMobileFriendly($("#result"));

    $("#copyBtn").disabled = false;
    setStatus("Done.", "ok");
  } catch (err) {
    setStatus(err.message || String(err), "err");
  } finally {
    $("#submitBtn").disabled = false;
  }
});

$("#copyBtn").addEventListener("click", async () => {
  if (!lastHTML) return;
  await navigator.clipboard.writeText(lastHTML);
  setStatus("HTML copied to clipboard.", "ok");
});
