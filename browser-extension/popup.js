import { quickCheck, summarise, SITE } from "./api.js";

const msg = document.getElementById("msg");
const btn = document.getElementById("check");
const out = document.getElementById("result");
document.getElementById("site").href = SITE;

function render(s, sourceText) {
  out.hidden = false;
  out.className = s.scam ? "scam" : "safe";
  out.replaceChildren();
  const h = document.createElement("h2");
  h.textContent = s.title;
  const p = document.createElement("p");
  p.className = "muted";
  p.textContent = s.detail + (sourceText ? ` — “${sourceText.slice(0, 60)}${sourceText.length > 60 ? "…" : ""}”` : "");
  out.append(h, p);
  if (s.actions.length) {
    const ul = document.createElement("ul");
    for (const a of s.actions) {
      const li = document.createElement("li");
      li.textContent = a;
      ul.append(li);
    }
    out.append(ul);
  }
}

btn.addEventListener("click", async () => {
  const text = msg.value.trim();
  if (text.length < 3) return;
  btn.disabled = true;
  btn.textContent = "Checking…";
  try {
    render(summarise(await quickCheck(text)));
  } catch {
    out.hidden = false;
    out.className = "";
    out.textContent = "Could not reach ScamGuard. The server may be waking up; try again in a few seconds.";
  } finally {
    btn.disabled = false;
    btn.textContent = "Check message";
  }
});

// Show the last right-click result, then clear the toolbar badge.
chrome.storage.local.get("last").then(({ last }) => {
  if (last && Date.now() - last.at < 10 * 60 * 1000) render(last, last.text);
  chrome.action.setBadgeText({ text: "" });
});
