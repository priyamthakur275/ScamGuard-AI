"use client";

import { useEffect, useMemo, useState } from "react";
import { RotateCcw } from "lucide-react";
import { riskScore } from "@/lib/api/tools";
import { cn } from "@/lib/utils";

type Trap = { find: string; fix: string; label: string; why: string };
type Case = { title: string; sender: string; realSender: string; text: string; traps: Trap[] };

/* Hand-written fixes, so the end result reads like a real notice. Every score
 * shown is computed live by the same engine as the rest of the site. */
const CASES: Case[] = [
  {
    title: "Bank KYC",
    sender: "+91 98765 41207",
    realSender: "VM-SBIBNK",
    text: "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone.",
    traps: [
      { find: "URGENT: ", fix: "", label: "Urgency", why: "Banks don't shout or rush you." },
      { find: "will be blocked today", fix: "KYC is due for renewal", label: "Threat", why: "A real notice gives a due date, not a same-day block." },
      { find: "Update KYC immediately at http://sbi-kyc-verify.xyz", fix: "Update it at your branch or in the YONO app", label: "Link", why: "KYC is done at the branch or in the official app, never through a link in an SMS." },
      { find: " and share the OTP sent to your phone.", fix: ". SBI never asks for your OTP.", label: "OTP request", why: "No bank ever asks for your OTP." },
    ],
  },
  {
    title: "Digital arrest",
    sender: "+91 70214 88310",
    realSender: "VM-MUMPOL",
    text: "This is CBI Mumbai. You are under digital arrest. Do not tell anyone. Transfer Rs 50,000 to the verification account.",
    traps: [
      { find: "This is CBI Mumbai.", fix: "Cyber awareness message from Mumbai Police:", label: "Fake authority", why: "CBI and the police don't arrest people over a phone message." },
      { find: "You are under digital arrest.", fix: "There is no such thing as a digital arrest.", label: "Legal threat", why: "'Digital arrest' does not exist in Indian law." },
      { find: "Do not tell anyone.", fix: "If anyone threatens you on a call, tell your family.", label: "Secrecy", why: "Scammers cut you off from help. Officials never ask you to hide it." },
      { find: "Transfer Rs 50,000 to the verification account.", fix: "Never transfer money on a call. Report fraud at 1930.", label: "Money request", why: "No agency asks you to move money to 'verify' it." },
    ],
  },
  {
    title: "Electricity cut",
    sender: "+91 91234 56780",
    realSender: "VM-BESCOM",
    text: "Dear customer, your electricity will be disconnected tonight at 9:30 pm. Call officer 9123456780 immediately to update your bill.",
    traps: [
      { find: "will be disconnected tonight at 9:30 pm", fix: "bill of Rs 1,240 is due on 5 Nov", label: "Threat", why: "Boards send a due date, not a same-night cut-off." },
      { find: "Call officer 9123456780 immediately to update your bill.", fix: "Pay in the official app or at any office counter. We never ask for payment over a call.", label: "Call this number", why: "Bills are paid in the official app or at the office, never to a mobile number." },
    ],
  },
];

const pct = (v: number) => Math.round(v * 100);

export function GenuineGame() {
  const [ci, setCi] = useState(0);
  const c = CASES[ci]!;
  const [fixed, setFixed] = useState<number[]>([]);
  const [scores, setScores] = useState<number[]>([]);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const text = useMemo(() => fixed.reduce((t, i) => t.replace(c.traps[i]!.find, c.traps[i]!.fix), c.text), [c, fixed]);
  const allFixed = fixed.length === c.traps.length;

  useEffect(() => {
    let live = true;
    setBusy(true);
    setError(false);
    riskScore(text)
      .then((r) => live && setScores((s) => { const n = s.slice(0, fixed.length); n[fixed.length] = r.score; return n; }))
      .catch(() => live && setError(true))
      .finally(() => live && setBusy(false));
    return () => { live = false; };
  }, [text, fixed.length]);

  const reset = (i = ci) => { setCi(i); setFixed([]); setScores([]); };
  const score = scores[fixed.length];

  // Split the current text into plain runs and clickable traps.
  const pieces = useMemo(() => {
    const hits = c.traps.map((t, i) => ({ i, at: fixed.includes(i) ? -1 : text.indexOf(t.find) })).filter((h) => h.at >= 0).sort((a, b) => a.at - b.at);
    const out: Array<string | number> = [];
    let at = 0;
    for (const h of hits) { out.push(text.slice(at, h.at), h.i); at = h.at + c.traps[h.i]!.find.length; }
    out.push(text.slice(at));
    return out;
  }, [c, text, fixed]);

  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-2">
        {CASES.map((x, i) => (
          <button key={x.title} type="button" onClick={() => reset(i)}
            className={cn("rounded-md border px-3 py-1.5 text-sm", i === ci ? "border-foreground font-medium text-foreground" : "border-border text-muted-foreground hover:text-foreground")}>
            {x.title}
          </button>
        ))}
      </div>

      <div className="mt-5 grid gap-6 md:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        {/* The message, as it would look on a phone */}
        <div className="rounded-xl border border-border bg-card">
          <div className="border-b border-border px-4 py-2.5 text-sm">
            <span className="text-muted-foreground">From </span>
            <span className="font-medium">{allFixed ? c.realSender : c.sender}</span>
          </div>
          <div className="p-4">
            <div className="rounded-lg rounded-tl-none bg-muted px-3.5 py-3 text-[15px] leading-relaxed">
              {pieces.map((p, k) => typeof p === "string" ? <span key={k}>{p}</span> : (
                <button key={k} type="button" onClick={() => setFixed((f) => [...f, p])} title={`Fix: ${c.traps[p]!.label}`}
                  className="rounded-sm bg-destructive/15 text-left text-destructive underline decoration-dotted underline-offset-2 hover:bg-destructive/25">
                  {c.traps[p]!.find.trim()}
                </button>
              ))}
            </div>
            {allFixed && <p className="mt-3 text-xs text-muted-foreground">A real notice would also come from a registered sender ID like {c.realSender}, not a mobile number.</p>}
          </div>
        </div>

        <div>
          <div className="flex items-baseline justify-between border-b border-border pb-3">
            <div>
              <p className="text-sm text-muted-foreground">Risk score</p>
              <p className={cn("text-3xl font-semibold tabular-nums", score === undefined ? "text-muted-foreground" : score >= 0.5 ? "text-destructive" : "text-safe")}>
                {score === undefined ? "–" : `${pct(score)}%`}
              </p>
            </div>
            <p className="text-sm">{score === undefined ? (busy ? "Checking…" : "") : score >= 0.5 ? "Reads as a scam" : "Reads as genuine"}</p>
          </div>
          {error && <p className="mt-3 text-sm text-destructive">Couldn&apos;t reach the server. It may be waking up; try again in a few seconds.</p>}

          {fixed.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">
              Tap a red part of the message to replace it with what the real {c.title === "Digital arrest" ? "police" : "company"} would write. Watch what it takes for the score to drop.
            </p>
          ) : (
            <ol className="mt-4 space-y-3 text-sm">
              {fixed.map((i, n) => (
                <li key={i} className="border-l-2 border-border pl-3">
                  <p className="flex justify-between gap-3">
                    <span className="font-medium">{n + 1}. {c.traps[i]!.label}</span>
                    {scores[n + 1] !== undefined && <span className="tabular-nums text-muted-foreground">{pct(scores[n] ?? 0)}% → {pct(scores[n + 1] ?? 0)}%</span>}
                  </p>
                  <p className="mt-0.5 text-muted-foreground">{c.traps[i]!.why}</p>
                </li>
              ))}
            </ol>
          )}

          {allFixed && score !== undefined && (
            <p className="mt-5 rounded-md bg-muted p-3 text-sm">
              Notice how the score stayed high until the last trap was gone. One trap is enough to make a message a scam, so check for every one of them.
            </p>
          )}
          {fixed.length > 0 && (
            <button type="button" onClick={() => reset()} className="mt-4 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
              <RotateCcw className="h-3.5 w-3.5" /> Start again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
