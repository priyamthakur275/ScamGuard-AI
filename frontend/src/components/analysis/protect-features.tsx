"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertOctagon, CheckSquare, Copy, Dna, ExternalLink, Eye, Phone, Square, Timer, X } from "lucide-react";
import type { AnalysisResult } from "@/types";

/* ------------------------------------------------------------------ */
/* Scam Forecast: what the scammer will most likely do next            */
/* ------------------------------------------------------------------ */
type Stage = "hook" | "pressure" | "ask" | "cashout";
interface XrayLike { spans?: { stage: Stage }[]; stages?: Partial<Record<Stage, string[]>> }

const NEXT_BY_CATEGORY: Record<string, string[]> = {
  banking_fraud: ["Ask for the OTP that just arrived on your phone", "Send a link to a fake bank page to 'complete KYC'", "Ask you to install AnyDesk or a 'support' app"],
  phishing: ["Ask you to log in on a look-alike page", "Capture your password and the OTP you type", "Use them to move money out within minutes"],
  job_scam: ["Pay you a small first 'reward' to win trust", "Ask for a bigger deposit to 'unlock tasks'", "Stop replying once you have paid"],
  investment_scam: ["Show fake profits in an app dashboard", "Ask for more money to 'withdraw' your profit", "Block you after the final deposit"],
  government_scam: ["Keep you on a video call and forbid you to tell family", "Ask you to move money to an 'RBI safe account'", "Threaten arrest if you hang up"],
  upi_scam: ["Send a UPI 'collect' request that looks like a refund", "Ask you to enter your UPI PIN to 'receive' money", "Repeat the request for a larger amount"],
  lottery_scam: ["Ask for a 'processing fee' or 'tax' to release the prize", "Ask for your bank details to 'transfer' the prize", "Ask for one more fee every time you pay"],
  fake_delivery: ["Ask for a small 'redelivery' or customs fee by link", "Capture your card details on the payment page", "Charge your card for much more"],
};

const NEXT_BY_STAGE: Record<Stage, string> = {
  hook: "Create urgency: a deadline, a threat to block your account, or a fine",
  pressure: "Ask for something only you have: an OTP, UPI PIN, password or card number",
  ask: "Take the money: a payment, a 'fee', a transfer or a fake link",
  cashout: "Push you to act right now, before you can check with anyone",
};

export function ScamForecast({ result }: { result: AnalysisResult }) {
  const xray = (result.metadata?.xray as XrayLike | undefined) ?? undefined;
  const steps = useMemo(() => {
    const byCat = result.scam_category ? NEXT_BY_CATEGORY[result.scam_category] : undefined;
    if (byCat) return byCat;
    const order: Stage[] = ["hook", "pressure", "ask", "cashout"];
    const seen = new Set((xray?.spans ?? []).map((s) => s.stage));
    const last = [...order].reverse().find((s) => seen.has(s)) ?? "hook";
    const from = order.indexOf(last);
    return order.slice(from).map((s) => NEXT_BY_STAGE[s]).slice(0, 3);
  }, [result.scam_category, xray]);

  if (result.verdict === "legitimate") return null;
  return (
    <div className="rounded-xl border border-risk-medium/40 bg-risk-medium/5 p-5">
      <p className="flex items-center gap-2 text-sm font-semibold">
        <Eye className="h-4 w-4 text-risk-medium" /> Scam Forecast: what they will try next
      </p>
      <ol className="mt-3 space-y-2">
        {steps.map((s, i) => (
          <li key={s} className="flex gap-3 text-sm">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-risk-medium/60 text-xs font-semibold text-risk-medium">{i + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-muted-foreground">Knowing the next move makes it easy to say no. Stop replying and do not share anything.</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Campaign fingerprint                                                */
/* ------------------------------------------------------------------ */
interface Campaign { id: string; name: string; goal: string; seen_30d: number }

export function CampaignFingerprint({ result }: { result: AnalysisResult }) {
  const c = result.metadata?.campaign as Campaign | undefined;
  if (!c || result.verdict === "legitimate") return null;
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-primary/40 bg-primary/5 p-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <Dna className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Known scam campaign</p>
          <p className="text-base font-semibold">{c.name}</p>
          <p className="text-sm text-muted-foreground">{c.goal}</p>
        </div>
      </div>
      <div className="shrink-0 text-left sm:text-right">
        <p className="font-display text-3xl font-bold tabular-nums text-primary">{c.seen_30d}</p>
        <p className="text-xs text-muted-foreground">scans of this campaign on ScamGuard in the last 30 days</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Golden Hour emergency mode                                          */
/* ------------------------------------------------------------------ */
const CHECKLIST = [
  "Call 1930 (National Cyber Crime Helpline) and read out the complaint below",
  "Call your bank's fraud helpline (number on the back of your card) and ask to block the card / freeze the transaction",
  "Change your UPI PIN and net-banking password; log out of other devices",
  "Uninstall any app the caller asked you to install (AnyDesk, TeamViewer, 'support' apps)",
  "File the complaint on cybercrime.gov.in and keep the acknowledgement number",
  "Save screenshots of the messages, numbers and transaction IDs",
];

export function GoldenHourButton({ result }: { result: AnalysisResult }) {
  const [open, setOpen] = useState(false);
  if (result.verdict === "legitimate") return null;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md border border-destructive/60 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive hover:bg-destructive/20"
      >
        <AlertOctagon className="h-4 w-4" /> I already paid / shared my OTP
      </button>
      {open && <GoldenHour result={result} onClose={() => setOpen(false)} />}
    </>
  );
}

function GoldenHour({ result, onClose }: { result: AnalysisResult; onClose: () => void }) {
  const [left, setLeft] = useState(60 * 60);
  const [done, setDone] = useState<boolean[]>(() => CHECKLIST.map(() => false));
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    const started = Date.now();
    const id = setInterval(() => setLeft(Math.max(0, 3600 - Math.floor((Date.now() - started) / 1000))), 1000);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => { clearInterval(id); window.removeEventListener("keydown", onKey); };
  }, [onClose]);

  const ents = (result.highlighted_entities ?? {}) as Record<string, string[] | undefined>;
  const list = (k: string) => (ents[k] ?? []).join(", ");
  const complaint = [
    "I received a fraudulent message and may have lost money / shared an OTP.",
    `Type of scam: ${result.scam_category ? result.scam_category.replace(/_/g, " ") : "online fraud"}.`,
    list("phones") && `Scammer phone number(s): ${list("phones")}.`,
    (list("urls") || list("shortened_links")) && `Link(s) used: ${[list("urls"), list("shortened_links")].filter(Boolean).join(", ")}.`,
    list("upi_ids") && `UPI ID(s): ${list("upi_ids")}.`,
    `Message received: "${(result.text || "").split(/\n\s*(Detected language\/concepts|Observed (URL|email|voice) signals)/)[0]!.replace(/^URL Target:\s*/, "").trim().slice(0, 400)}"`,
    "Transaction ID / amount / time: ________",
  ].filter(Boolean).join("\n");

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Golden hour emergency steps">
      <div className="relative my-6 w-full max-w-2xl rounded-2xl border border-destructive/50 bg-card p-6 shadow-2xl">
        <button onClick={onClose} className="absolute right-4 top-4 text-muted-foreground hover:text-foreground" aria-label="Close"><X className="h-5 w-5" /></button>
        <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-destructive"><Timer className="h-4 w-4" /> Golden hour</p>
        <h2 className="mt-1 text-2xl font-semibold">Act now. Money reported fast can often be frozen.</h2>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <p className="font-mono text-5xl font-bold tabular-nums text-destructive" aria-live="polite">{mm}:{ss}</p>
          <p className="max-w-xs text-sm text-muted-foreground">Report within the first hour. Banks and the 1930 helpline can put a hold on the money while it is still moving.</p>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <a href="tel:1930" className="flex items-center justify-center gap-2 rounded-xl bg-destructive px-4 py-3 text-base font-semibold text-destructive-foreground">
            <Phone className="h-5 w-5" /> Call 1930 now
          </a>
          <a href="https://cybercrime.gov.in" target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 rounded-xl border border-border px-4 py-3 text-base font-semibold">
            <ExternalLink className="h-5 w-5" /> cybercrime.gov.in
          </a>
        </div>
        <p className="mt-6 text-sm font-semibold">Do these now</p>
        <ul className="mt-2 space-y-2">
          {CHECKLIST.map((item, i) => (
            <li key={item}>
              <button type="button" onClick={() => setDone((d) => d.map((v, j) => (j === i ? !v : v)))} className="flex w-full items-start gap-3 text-left text-sm">
                {done[i] ? <CheckSquare className="mt-0.5 h-4 w-4 shrink-0 text-risk-low" /> : <Square className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />}
                <span className={done[i] ? "text-muted-foreground line-through" : ""}>{item}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm font-semibold">Complaint, ready to read out or paste</p>
          <button
            type="button"
            onClick={() => { navigator.clipboard?.writeText(complaint).then(() => setCopied(true)).catch(() => {}); }}
            className="inline-flex items-center gap-1.5 text-xs text-primary"
          >
            <Copy className="h-3.5 w-3.5" /> {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-background/60 p-3 text-xs leading-5">{complaint}</pre>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Elder mode: bigger, simpler, spoken                                  */
/* ------------------------------------------------------------------ */
const ELDER_KEY = "scamguard_elder_mode";

export function useElderMode(): [boolean, (v: boolean) => void] {
  const [on, setOn] = useState(false);
  useEffect(() => {
    try { setOn(localStorage.getItem(ELDER_KEY) === "1"); } catch {}
    const sync = () => { try { setOn(localStorage.getItem(ELDER_KEY) === "1"); } catch {} };
    window.addEventListener("sg-elder", sync);
    return () => window.removeEventListener("sg-elder", sync);
  }, []);
  useEffect(() => { document.documentElement.classList.toggle("elder", on); }, [on]);
  const set = (v: boolean) => {
    try { localStorage.setItem(ELDER_KEY, v ? "1" : "0"); } catch {}
    setOn(v);
    window.dispatchEvent(new Event("sg-elder"));
  };
  return [on, set];
}

export function ElderToggle() {
  const [on, set] = useElderMode();
  return (
    <button
      type="button"
      onClick={() => set(!on)}
      aria-pressed={on}
      title="Elder mode: bigger text, simpler screens"
      className={`whitespace-nowrap rounded-md border px-2 py-1.5 text-xs font-semibold sm:px-2.5 ${on ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
    >
      <span className="sm:hidden">{on ? "Elder ✓" : "Elder"}</span>
      <span className="hidden sm:inline">{on ? "Elder mode on" : "Elder mode"}</span>
    </button>
  );
}
