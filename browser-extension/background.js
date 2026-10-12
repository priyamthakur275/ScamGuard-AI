import { quickCheck, summarise } from "./api.js";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "sg-text", title: "Check selected text with ScamGuard", contexts: ["selection"] });
  chrome.contextMenus.create({ id: "sg-link", title: "Check this link with ScamGuard", contexts: ["link"] });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  const text = info.menuItemId === "sg-link" ? info.linkUrl : info.selectionText;
  if (!text || text.trim().length < 3) return;
  await chrome.action.setBadgeText({ text: "…" });
  try {
    const result = await quickCheck(text);
    const s = summarise(result);
    await chrome.storage.local.set({ last: { text, ...s, at: Date.now() } });
    await chrome.action.setBadgeBackgroundColor({ color: s.scam ? "#d93025" : "#188038" });
    await chrome.action.setBadgeText({ text: s.scam ? "!" : "OK" });
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon-128.png",
      title: `ScamGuard: ${s.title}`,
      message: `${s.detail}${s.actions[0] ? ` — ${s.actions[0]}` : ""}`,
      priority: s.scam ? 2 : 0,
    });
  } catch (err) {
    await chrome.action.setBadgeText({ text: "" });
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon-128.png",
      title: "ScamGuard could not check this",
      message: "The server may be waking up. Try again in a few seconds.",
    });
  }
});
