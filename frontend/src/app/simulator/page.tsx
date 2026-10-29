"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { IndianRupee, Loader2, MessageSquareWarning, Phone, RotateCcw, ScanSearch, ShieldCheck, ShieldX, Trophy } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { ErrorBoundary } from "@/components/error-boundary";
import { useCopilot } from "@/components/copilot/copilot-provider";
import { analyzeWithCopilot } from "@/lib/copilot/stream";
import type { MatchedTactic } from "@/lib/copilot/types";
import { cn } from "@/lib/utils";

type Choice = { text: string; safe: boolean; why: string; loss?: number };
type Turn = { scammer: string; choices: Choice[] };
type Scenario = { id: string; title: string; channel: "call" | "whatsapp" | "sms"; caller: string; intro: string; lesson: string; turns: Turn[] };

const SCENARIOS: Scenario[] = [
  {
    id: "bank",
    title: "Bank KYC call",
    channel: "call",
    caller: "+91 98xxx 41207 · 'SBI KYC Desk'",
    intro: "A caller says your SBI account will be blocked today.",
    lesson: "Banks never update KYC or ask for an OTP over a call. Hang up and use the official app or branch.",
    turns: [
      {
        scammer: "Hello sir, this is Rahul from SBI head office. Your KYC has expired and your account will be blocked in 2 hours. I will help you update it right now.",
        choices: [
          { text: "Okay, please help me update it quickly.", safe: false, why: "Banks never call to 'update KYC', and the 2-hour deadline is there to rush you." },
          { text: "I will visit my branch or use the official YONO app myself.", safe: true, why: "Right. KYC is done only at the branch or in the official app you open yourself." },
          { text: "Which branch are you calling from?", safe: false, why: "Questions keep you on the call, and scammers have ready answers. Just hang up." },
        ],
      },
      {
        scammer: "Sir, no need to visit. I have sent a 6-digit code to your phone for verification. Please read it to me so I can stop the block.",
        choices: [
          { text: "Reads out the OTP.", safe: false, loss: 49999, why: "That OTP approved a transfer of Rs 49,999 from your account. No bank employee ever needs it." },
          { text: "No. I never share OTPs. I am hanging up.", safe: true, why: "Perfect. Nobody genuine will ever ask for an OTP." },
          { text: "Let me first check the message.", safe: false, why: "The message itself says 'do not share this OTP'. There is nothing to check: hang up." },
        ],
      },
      {
        scammer: "Sir, if you don't cooperate, your account and Aadhaar will be frozen and police action will follow.",
        choices: [
          { text: "Hang up, block the number and report it on Chakshu.", safe: true, why: "Excellent. Reporting on Chakshu helps get the number blocked for everyone." },
          { text: "Please don't, I will do whatever you say.", safe: false, loss: 25000, why: "Fear is the lever. The 'penalty' you were asked to pay next was Rs 25,000." },
        ],
      },
    ],
  },
  {
    id: "job",
    title: "WhatsApp task job",
    channel: "whatsapp",
    caller: "WhatsApp · 'Priya HR – Flipkart'",
    intro: "A stranger offers easy money for liking YouTube videos.",
    lesson: "A job that asks you to pay first is not a job. The small first payout is bait.",
    turns: [
      {
        scammer: "Hi! Earn Rs 3,000/day from home. Just like YouTube videos, Rs 50 per like. Interested?",
        choices: [
          { text: "Yes! What do I do?", safe: false, why: "Real companies don't hire strangers on WhatsApp to 'like' videos. This is the hook." },
          { text: "No thanks. Block and report the number.", safe: true, why: "Right. Unsolicited 'easy money' offers are task scams." },
        ],
      },
      {
        scammer: "Great, you earned Rs 150 for 3 likes! Sent to your UPI. To unlock premium tasks with Rs 5,000 commission, deposit Rs 1,000 first.",
        choices: [
          { text: "I got paid, so it's real. I'll deposit.", safe: false, loss: 1000, why: "The Rs 150 was bait to win your trust. Your Rs 1,000 is gone." },
          { text: "A job that asks me to pay is not a job. Stop.", safe: true, why: "Exactly. Real jobs never ask for a deposit or registration fee." },
        ],
      },
      {
        scammer: "Your money is stuck because of a 'tax'. Pay Rs 8,000 more to withdraw everything.",
        choices: [
          { text: "Pay once more to get it all back.", safe: false, loss: 8000, why: "There is no withdrawal. Every payment is followed by another fee." },
          { text: "Stop paying, save screenshots, call 1930 and file on cybercrime.gov.in.", safe: true, why: "Correct. Report quickly with transaction IDs; the money may still be frozen." },
        ],
      },
    ],
  },
  {
    id: "arrest",
    title: "'Digital arrest' video call",
    channel: "call",
    caller: "Video call · 'Mumbai Cyber Crime'",
    intro: "A man in police uniform says a parcel with drugs was booked on your Aadhaar.",
    lesson: "'Digital arrest' does not exist in Indian law. Police never keep you on a video call or ask you to move money.",
    turns: [
      {
        scammer: "This is Inspector Sharma, Mumbai Cyber Crime. A parcel with drugs in your name was seized. You are under digital arrest. Do not disconnect.",
        choices: [
          { text: "Stay on the call and follow instructions.", safe: false, why: "Police never arrest anyone over a video call. Staying on is how victims get trapped for hours." },
          { text: "Disconnect and call a trusted person and 1930.", safe: true, why: "Right. Breaking the isolation is the most important step." },
        ],
      },
      {
        scammer: "Don't tell anyone, this is confidential. To clear your name, transfer your savings to an RBI safe account for verification. It will be returned.",
        choices: [
          { text: "Transfer the money to prove innocence.", safe: false, loss: 350000, why: "There is no 'RBI safe account'. Victims of this scam often lose their whole savings." },
          { text: "Refuse. Secrecy plus a 'safe account' means scam. Report it.", safe: true, why: "Perfect. Keeping secrets and moving money are both clear signs of fraud." },
        ],
      },
    ],
  },
  {
    id: "upi",
    title: "'Sent by mistake' UPI",
    channel: "sms",
    caller: "SMS + call · unknown number",
    intro: "You get a credit SMS, then a call asking you to return the money.",
    lesson: "Check your own bank app before believing any credit SMS. You never enter a UPI PIN to receive money.",
    turns: [
      {
        scammer: "Rs 5,000 credited to your A/c XX1234 by mistake. Bhaiya please return it, it was for my mother's hospital. I am sending you a request now.",
        choices: [
          { text: "Open my bank app and check the balance first.", safe: true, why: "Right. The SMS is usually fake; your real balance shows nothing was credited." },
          { text: "Poor guy, I'll send it back right away.", safe: false, loss: 5000, why: "Nothing was ever credited. You just sent Rs 5,000 of your own money." },
        ],
      },
      {
        scammer: "Please approve the request on PhonePe and enter your UPI PIN, then the money will go back automatically.",
        choices: [
          { text: "Approve the request and enter my PIN.", safe: false, loss: 5000, why: "A collect request plus your PIN sends money out of your account. A PIN is never needed to receive." },
          { text: "Decline the request. Tell him to contact his bank.", safe: true, why: "Correct. A genuine wrong transfer is reversed by the bank, not by you." },
        ],
      },
    ],
  },
  {
    id: "power",
    title: "Electricity cut tonight",
    channel: "sms",
    caller: "SMS · 'BESCOM Officer'",
    intro: "An SMS says your power will be cut tonight for an unpaid bill.",
    lesson: "Utilities don't threaten disconnection from personal numbers. Pay only through the official app or website.",
    turns: [
      {
        scammer: "Dear consumer, your electricity will be disconnected tonight at 9:30 pm as last month's bill is not updated. Contact our officer immediately.",
        choices: [
          { text: "Call the number in the SMS.", safe: false, why: "The number belongs to the scammer. The official helpline is on your bill and the BESCOM website." },
          { text: "Check my bill in the official BESCOM app.", safe: true, why: "Right. The official app shows your real dues." },
        ],
      },
      {
        scammer: "Sir, to update your bill please install the 'Quick Support' app and tell me the code. I will do it for you.",
        choices: [
          { text: "Install it, he's only helping.", safe: false, loss: 20000, why: "Screen-sharing apps let the caller watch your OTPs and empty your account." },
          { text: "Never install apps a caller asks for. Hang up.", safe: true, why: "Correct. No genuine officer needs remote access to your phone." },
        ],
      },
    ],
  },
];

type LogItem = { who: "scammer" | "you"; text: string; choice?: Choice; turnIndex?: number };
type Scan = { state: "loading" } | { state: "done"; fraud: number; tactics: MatchedTactic[] } | { state: "error" };

function shuffle<T>(items: T[], seed: number): T[] {
  const out = [...items];
  let s = seed;
  for (let i = out.length - 1; i > 0; i--) {
    s = (s * 9301 + 49297) % 233280;
    const j = Math.floor((s / 233280) * (i + 1));
    [out[i], out[j]] = [out[j] as T, out[i] as T];
  }
  return out;
}

function rupees(n: number): string {
  return `Rs ${n.toLocaleString("en-IN")}`;
}

function Highlighted({ text, tactics }: { text: string; tactics: MatchedTactic[] }) {
  const phrases = tactics.map((t) => t.evidence).filter((e) => e && e.length > 1 && text.includes(e));
  if (!phrases.length) return <>{text}</>;
  const pattern = new RegExp(`(${phrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
  return (
    <>
      {text.split(pattern).map((part, i) =>
        phrases.includes(part) ? (
          <mark key={i} className="rounded bg-risk-high/20 px-0.5 text-foreground underline decoration-risk-high decoration-2 underline-offset-2">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

function EngineReading({ scan, show }: { scan: Scan | undefined; show: boolean }) {
  if (!show || !scan) return null;
  if (scan.state === "loading") {
    return (
      <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> ScamGuard is checking this line…
      </p>
    );
  }
  if (scan.state === "error") return <p className="mt-2 text-xs text-muted-foreground">ScamGuard could not check this line right now.</p>;
  return (
    <div className="mt-2 rounded-lg border border-border bg-background/60 px-2.5 py-2 text-xs">
      <p className="flex items-center gap-1.5 font-medium">
        <ScanSearch className="h-3.5 w-3.5 text-primary" />
        ScamGuard: <span className={scan.fraud >= 50 ? "text-risk-high" : "text-risk-low"}>{scan.fraud}% fraud index</span>
      </p>
      {scan.tactics.length > 0 && <p className="mt-1 text-muted-foreground">{scan.tactics.map((t) => t.label).join(" · ")}</p>}
    </div>
  );
}

function SimulatorGame() {
  const { setOpen } = useCopilot();
  const [sid, setSid] = useState(SCENARIOS[0]!.id);
  const scenario = SCENARIOS.find((s) => s.id === sid) ?? SCENARIOS[0]!;
  const [turn, setTurn] = useState(0);
  const [log, setLog] = useState<LogItem[]>([]);
  const [score, setScore] = useState(0);
  const [lost, setLost] = useState(0);
  const [seed, setSeed] = useState(1);
  const [showEngine, setShowEngine] = useState(true);
  const [scans, setScans] = useState<Record<string, Scan>>({});
  const endRef = useRef<HTMLDivElement>(null);
  const requested = useRef<Set<string>>(new Set());

  const scanLine = useCallback((line: string) => {
    if (requested.current.has(line)) return;
    requested.current.add(line);
    setScans((s) => ({ ...s, [line]: { state: "loading" } }));
    analyzeWithCopilot(line)
      .then((res) => setScans((s) => ({ ...s, [line]: { state: "done", fraud: res.verdict.fraud_index, tactics: res.verdict.matched_tactics } })))
      .catch(() => {
        requested.current.delete(line);
        setScans((s) => ({ ...s, [line]: { state: "error" } }));
      });
  }, []);

  const reset = useCallback(
    (id: string) => {
      const sc = SCENARIOS.find((s) => s.id === id) ?? SCENARIOS[0]!;
      setSid(sc.id);
      setTurn(0);
      setScore(0);
      setLost(0);
      setSeed(Date.now() % 233280);
      setLog([{ who: "scammer", text: sc.turns[0]!.scammer, turnIndex: 0 }]);
      if (showEngine) scanLine(sc.turns[0]!.scammer);
    },
    [scanLine, showEngine],
  );

  useEffect(() => {
    reset(SCENARIOS[0]!.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [log]);

  const finished = turn >= scenario.turns.length;
  const current = finished ? null : scenario.turns[turn];
  const choices = useMemo(() => (current ? shuffle(current.choices, seed + turn) : []), [current, seed, turn]);

  const pick = (c: Choice) => {
    const nextTurn = turn + 1;
    const add: LogItem[] = [{ who: "you", text: c.text, choice: c }];
    const next = scenario.turns[nextTurn];
    if (next) {
      add.push({ who: "scammer", text: next.scammer, turnIndex: nextTurn });
      if (showEngine) scanLine(next.scammer);
    }
    setLog((l) => [...l, ...add]);
    if (c.safe) setScore((s) => s + 1);
    if (!c.safe && c.loss) setLost((v) => v + (c.loss ?? 0));
    setTurn(nextTurn);
  };

  const toggleEngine = () => {
    const next = !showEngine;
    setShowEngine(next);
    if (next) log.filter((m) => m.who === "scammer").forEach((m) => scanLine(m.text));
  };

  const total = scenario.turns.length;
  const verdict =
    score === total
      ? "Scam-proof. You didn't fall for a single trick."
      : lost > 0
        ? `The scammer would have taken ${rupees(lost)} from you.`
        : "Almost safe, but one answer kept you on the hook.";
  const ChannelIcon = scenario.channel === "call" ? Phone : MessageSquareWarning;

  return (
    <>
      <div className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Scenarios">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={s.id === sid}
            onClick={() => reset(s.id)}
            className={cn("rounded-full border px-4 py-2 text-sm", s.id === sid ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground hover:text-foreground")}
          >
            {s.title}
          </button>
        ))}
      </div>

      <section className="sg-card mt-6 rounded-2xl border border-border p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-risk-high/15 text-risk-high">
              <ChannelIcon className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold">{scenario.caller}</p>
              <p className="text-xs text-muted-foreground">{scenario.intro}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm tabular-nums">
            <span className="text-muted-foreground">Safe {score}/{total}</span>
            <span className={cn("inline-flex items-center gap-1", lost > 0 ? "font-semibold text-risk-high" : "text-muted-foreground")} aria-live="polite">
              <IndianRupee className="h-3.5 w-3.5" /> {lost > 0 ? `${lost.toLocaleString("en-IN")} lost` : "0 lost"}
            </span>
          </div>
        </div>

        <label className="mt-3 flex w-fit cursor-pointer items-center gap-2 text-xs text-muted-foreground">
          <input type="checkbox" checked={showEngine} onChange={toggleEngine} className="accent-[hsl(var(--primary))]" />
          Show what ScamGuard&apos;s engine sees in each scammer line
        </label>

        <div className="mt-4 space-y-3" aria-live="polite">
          {log.map((m, i) => {
            const scan = scans[m.text];
            const tactics = showEngine && scan?.state === "done" ? scan.tactics : [];
            return (
              <div key={i} className={cn("flex", m.who === "you" ? "justify-end" : "justify-start")}>
                <div className={cn("max-w-[85%] rounded-2xl px-4 py-3 text-sm", m.who === "you" ? "border border-primary/40 bg-primary/10" : "border border-border bg-muted/50")}>
                  <p>{m.who === "scammer" ? <Highlighted text={m.text} tactics={tactics} /> : m.text}</p>
                  {m.who === "scammer" && <EngineReading scan={scan} show={showEngine} />}
                  {m.choice && (
                    <p className={cn("mt-2 flex items-start gap-1.5 text-xs", m.choice.safe ? "text-risk-low" : "text-destructive")}>
                      {m.choice.safe ? <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <ShieldX className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
                      {m.choice.why}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>

        {current && (
          <div className="mt-5 grid gap-2">
            <p className="text-xs text-muted-foreground">Your reply:</p>
            {choices.map((c) => (
              <button key={c.text} onClick={() => pick(c)} className="rounded-xl border border-border px-4 py-3 text-left text-sm transition-colors hover:border-primary hover:bg-primary/5">
                {c.text}
              </button>
            ))}
          </div>
        )}

        {finished && (
          <div className="mt-6 space-y-4 rounded-xl border border-primary/40 bg-primary/5 p-5">
            <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <Trophy className={cn("h-6 w-6", score === total ? "text-primary" : "text-muted-foreground")} />
                <div>
                  <p className="font-semibold">You scored {score} / {total}</p>
                  <p className={cn("text-sm", lost > 0 ? "text-risk-high" : "text-muted-foreground")}>{verdict}</p>
                </div>
              </div>
              <button onClick={() => reset(scenario.id)} className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm hover:border-primary">
                <RotateCcw className="h-4 w-4" /> Play again
              </button>
            </div>
            <p className="border-t border-border pt-3 text-sm"><b>Remember:</b> {scenario.lesson}</p>
            <div className="flex flex-wrap gap-2 text-sm">
              <button type="button" onClick={() => setOpen(true)} className="rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground">
                Got a real message? Ask Copilot
              </button>
              <Link href="/#quick-check" className="rounded-md border border-border px-4 py-2 hover:border-primary">Quick check a message</Link>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

export default function SimulatorPage() {
  return (
    <PublicShell>
      <p className="text-xs text-primary">Practice safely</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Scam simulator</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Talk to a scripted scammer and choose your replies. Each answer is scored and explained, wrong answers show what you would have lost, and
        ScamGuard&apos;s real detection engine marks the traps in every scammer line as the conversation goes on.
      </p>
      <ErrorBoundary area="The simulator">
        <SimulatorGame />
      </ErrorBoundary>
    </PublicShell>
  );
}
