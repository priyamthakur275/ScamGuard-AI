"use client";

import { useEffect, useRef, useState } from "react";
import { RotateCcw, ShieldCheck, ShieldX, Trophy } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { cn } from "@/lib/utils";

type Choice = { text: string; safe: boolean; why: string; next?: number };
type Turn = { scammer: string; choices: Choice[] };
type Scenario = { id: string; title: string; caller: string; intro: string; turns: Turn[] };

const SCENARIOS: Scenario[] = [
  {
    id: "bank",
    title: "Fake bank KYC call",
    caller: "+91 98xxx 41207 · 'SBI KYC Desk'",
    intro: "A caller says your SBI account will be blocked today.",
    turns: [
      {
        scammer: "Hello sir, this is Rahul from SBI head office. Your KYC has expired and your account will be blocked in 2 hours. I will help you update it right now.",
        choices: [
          { text: "Okay, please help me update it quickly.", safe: false, why: "Banks never call to 'update KYC' on the phone, and the 2-hour deadline is pressure." },
          { text: "I will visit my branch or use the official YONO app myself.", safe: true, why: "Right. KYC is only done at the branch or in the official app you open yourself." },
          { text: "Which branch are you calling from?", safe: false, why: "Asking questions keeps you on the call. Scammers have ready answers. Just hang up." },
        ],
      },
      {
        scammer: "Sir, no need to visit. I have sent a 6-digit code to your phone for verification. Please read it to me so I can stop the block.",
        choices: [
          { text: "Reads out the OTP.", safe: false, why: "An OTP is the key to your money. With it they can complete a transfer instantly." },
          { text: "No. I never share OTPs. I am hanging up.", safe: true, why: "Perfect. No genuine bank employee will ever ask for an OTP." },
          { text: "Let me first check the message.", safe: false, why: "The message itself says 'do not share this OTP'. There is nothing to check: hang up." },
        ],
      },
      {
        scammer: "Sir, if you don't cooperate, your account and Aadhaar will be frozen and police action will follow.",
        choices: [
          { text: "Hang up, block the number and report it on Chakshu / 1930.", safe: true, why: "Excellent. Reporting helps get the number blocked for everyone." },
          { text: "Please don't, I will do whatever you say.", safe: false, why: "Threats are the oldest trick. Banks do not threaten police action on a call." },
        ],
      },
    ],
  },
  {
    id: "job",
    title: "Part-time job on WhatsApp",
    caller: "WhatsApp · 'Priya HR – Flipkart'",
    intro: "A stranger offers easy money for liking YouTube videos.",
    turns: [
      {
        scammer: "Hi! Earn Rs 3,000/day from home. Just like YouTube videos, Rs 50 per like. Interested?",
        choices: [
          { text: "Yes! What do I do?", safe: false, why: "Real companies don't hire strangers on WhatsApp to 'like' videos. This is the hook." },
          { text: "No thanks. Blocks and reports the number.", safe: true, why: "Right. Unsolicited 'easy money' offers are task scams." },
        ],
      },
      {
        scammer: "Great, you earned Rs 150 for 3 likes! Sent to your UPI. To unlock premium tasks with Rs 5,000 commission, deposit Rs 1,000 first.",
        choices: [
          { text: "I got paid, so it's real. I'll deposit.", safe: false, why: "The small first payment is bait. After the deposit, 'bigger tasks' need bigger deposits, then they vanish." },
          { text: "A job that asks me to pay is not a job. Stop.", safe: true, why: "Exactly. Real jobs never ask for a deposit or registration fee." },
        ],
      },
      {
        scammer: "Your money is stuck because of a 'tax'. Pay Rs 8,000 more to withdraw everything.",
        choices: [
          { text: "Pay once more to get it all back.", safe: false, why: "There is no withdrawal. Every payment is followed by another fee." },
          { text: "Stop paying, collect screenshots, call 1930 and file on cybercrime.gov.in.", safe: true, why: "Correct. Report quickly with transaction IDs; the money may still be frozen." },
        ],
      },
    ],
  },
  {
    id: "arrest",
    title: "'Digital arrest' video call",
    caller: "Video call · 'Mumbai Cyber Crime'",
    intro: "A man in a police uniform says a parcel with drugs was booked on your Aadhaar.",
    turns: [
      {
        scammer: "This is Inspector Sharma, Mumbai Cyber Crime. A parcel with drugs in your name was seized. You are under digital arrest. Do not disconnect.",
        choices: [
          { text: "Stay on the call and follow instructions.", safe: false, why: "'Digital arrest' does not exist in Indian law. Police never arrest anyone over a video call." },
          { text: "Disconnect and call a family member and 1930.", safe: true, why: "Right. Breaking the isolation is the most important step." },
        ],
      },
      {
        scammer: "Don't tell anyone, this is confidential. To clear your name, transfer your savings to an RBI safe account for verification. It will be returned.",
        choices: [
          { text: "Transfer the money to prove innocence.", safe: false, why: "There is no 'RBI safe account'. RBI never holds money for verification." },
          { text: "Refuse. Secrecy + 'safe account' = scam. Report it.", safe: true, why: "Perfect. Asking you to keep secrets and move money are both clear signs of fraud." },
        ],
      },
    ],
  },
];

export default function SimulatorPage() {
  const [sid, setSid] = useState(SCENARIOS[0]!.id);
  const scenario = SCENARIOS.find((s) => s.id === sid) ?? SCENARIOS[0]!;
  const [turn, setTurn] = useState(0);
  const [log, setLog] = useState<{ who: "scammer" | "you"; text: string; choice?: Choice }[]>([]);
  const [score, setScore] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);

  const reset = (id = sid) => {
    const sc = SCENARIOS.find((s) => s.id === id) ?? SCENARIOS[0]!;
    setSid(id);
    setTurn(0);
    setScore(0);
    setLog([{ who: "scammer", text: sc.turns[0]!.scammer }]);
  };
  useEffect(() => reset(SCENARIOS[0]!.id), []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), [log]);

  const finished = turn >= scenario.turns.length;
  const current = finished ? null : scenario.turns[turn];

  const pick = (c: Choice) => {
    const nextTurn = turn + 1;
    const add: typeof log = [{ who: "you", text: c.text, choice: c }];
    const nxt = scenario.turns[nextTurn];
    if (nxt) add.push({ who: "scammer", text: nxt.scammer });
    setLog((l) => [...l, ...add]);
    if (c.safe) setScore((s) => s + 1);
    setTurn(nextTurn);
  };

  const total = scenario.turns.length;
  const verdict = score === total ? "Scam-proof! You didn't fall for a single trick." : score >= total - 1 ? "Almost safe. One answer would have cost you." : "The scammer would have won this time. Try again.";

  return (
    <PublicShell>
      <p className="text-xs text-primary">Practice safely</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Scam simulator</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Talk to a scripted scammer and choose your replies. Each answer is scored and explained, so you learn the tricks before a real scammer tries them on you.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => reset(s.id)}
            className={cn("rounded-full border px-4 py-2 text-sm", s.id === sid ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground hover:text-foreground")}
          >
            {s.title}
          </button>
        ))}
      </div>

      <section className="sg-card mt-6 rounded-2xl border border-border p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
          <div>
            <p className="text-sm font-semibold">{scenario.caller}</p>
            <p className="text-xs text-muted-foreground">{scenario.intro}</p>
          </div>
          <p className="text-sm tabular-nums text-muted-foreground">Safe answers {score} / {total}</p>
        </div>

        <div className="mt-4 space-y-3" aria-live="polite">
          {log.map((m, i) => (
            <div key={i} className={cn("flex", m.who === "you" ? "justify-end" : "justify-start")}>
              <div className={cn("max-w-[85%] rounded-2xl px-4 py-3 text-sm", m.who === "you" ? "border border-primary/40 bg-primary/10" : "border border-border bg-muted/50")}>
                <p>{m.text}</p>
                {m.choice && (
                  <p className={cn("mt-2 flex items-start gap-1.5 text-xs", m.choice.safe ? "text-risk-low" : "text-destructive")}>
                    {m.choice.safe ? <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <ShieldX className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
                    {m.choice.why}
                  </p>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        {current && (
          <div className="mt-5 grid gap-2">
            <p className="text-xs text-muted-foreground">Your reply:</p>
            {current.choices.map((c) => (
              <button key={c.text} onClick={() => pick(c)} className="rounded-xl border border-border px-4 py-3 text-left text-sm transition-colors hover:border-primary hover:bg-primary/5">
                {c.text}
              </button>
            ))}
          </div>
        )}

        {finished && (
          <div className="mt-6 flex flex-col items-start gap-3 rounded-xl border border-primary/40 bg-primary/5 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <Trophy className="h-6 w-6 text-primary" />
              <div>
                <p className="font-semibold">You scored {score} / {total}</p>
                <p className="text-sm text-muted-foreground">{verdict}</p>
              </div>
            </div>
            <button onClick={() => reset()} className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm hover:border-primary">
              <RotateCcw className="h-4 w-4" /> Play again
            </button>
          </div>
        )}
      </section>
    </PublicShell>
  );
}
