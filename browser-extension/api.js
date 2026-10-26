// Shared by the popup and the background worker.
export const SITE = "https://scamguard-ai-zeta.vercel.app";
const ENDPOINT = `${SITE}/backend-api/api/v1/public/quick-check`;

export async function quickCheck(text) {
  const body = JSON.stringify({ text: String(text).slice(0, 2000) });
  // The free server may be waking up: retry a few times before giving up.
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const res = await fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body });
      if (res.ok) return await res.json();
      if (![429, 502, 503, 504].includes(res.status)) throw new Error(`Server returned ${res.status}`);
    } catch (err) {
      if (attempt === 3) throw err;
    }
    await new Promise((r) => setTimeout(r, 1500 * 2 ** attempt));
  }
  throw new Error("ScamGuard is not reachable right now.");
}

export function summarise(result) {
  const scam = result.verdict !== "legitimate";
  const pct = Math.round((result.threat_score ?? 0) * 100);
  const category = result.scam_category ? result.scam_category.replace(/_/g, " ") : "";
  return {
    scam,
    title: scam ? `Likely scam${category ? ` · ${category}` : ""}` : "Looks legitimate",
    detail: `${pct}% scam likelihood`,
    actions: scam ? (result.recommended_actions || []).slice(0, 3) : [],
  };
}
