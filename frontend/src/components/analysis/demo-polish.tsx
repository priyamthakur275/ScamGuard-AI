"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Loader2, Volume2, VolumeX } from "lucide-react";
import { ThreatCoreCanvas } from "@/components/visuals/threat-core-canvas";

/* ------------------------------------------------------------------ */
/* 1. Count-up number for the verdict score                            */
/* ------------------------------------------------------------------ */
export function CountUp({ value, duration = 900 }: { value: number; duration?: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setShown(value);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{shown}</>;
}

/* ------------------------------------------------------------------ */
/* 2. Step-by-step progress while a scan runs                          */
/* ------------------------------------------------------------------ */
const STEPS: Record<string, string[]> = {
  image: ["Reading the screenshot (OCR)", "Separating sender and your replies", "Running the ML model", "Checking scam intent", "Preparing the verdict"],
  pdf: ["Extracting text from the PDF", "Running the ML model", "Checking scam intent", "Preparing the verdict"],
  qr: ["Decoding the QR code", "Checking the link it points to", "Running the ML model", "Preparing the verdict"],
  url: ["Checking the link structure", "Opening the page safely", "Looking up domain age", "Scoring website trust", "Preparing the verdict"],
  email: ["Reading sender and headers", "Checking links in the email", "Running the ML model", "Checking scam intent", "Preparing the verdict"],
  voice: ["Reading the call transcript", "Running the ML model", "Checking scam intent", "Preparing the verdict"],
  text: ["Reading the message", "Running the ML model", "Checking scam intent", "Building the Scam X-Ray", "Preparing the verdict"],
};

export function ScanProgress({ channel, label }: { channel: string; label?: string }) {
  const steps: string[] = STEPS[channel] ?? STEPS.text ?? [];
  const [step, setStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const started = Date.now();
    const id = setInterval(() => {
      const s = (Date.now() - started) / 1000;
      setElapsed(s);
      setStep(Math.min(steps.length - 1, Math.floor(s / 0.9)));
    }, 250);
    return () => clearInterval(id);
  }, [steps.length]);

  return (
    <div className="scanner-panel sg-scan-beam px-6 py-8" role="status" aria-live="polite">
      <div className="mx-auto flex max-w-2xl flex-col items-center text-center">
        <div className="h-36 w-36">
          <ThreatCoreCanvas mode="scanning" active />
        </div>
        <div className="mt-2 flex items-center gap-2 font-mono text-xs text-primary">
          <span>ACTIVE PIPELINE · {channel.toUpperCase()}</span>
          {label && <span>· {label}</span>}
          <span className="tabular-nums">· {elapsed.toFixed(1)}s</span>
        </div>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground">Scanning &amp; Analyzing…</h2>
        <p className="mt-1 text-sm text-muted-foreground">{steps[step] ?? "Processing evidence…"}</p>
      </div>

      {/* Horizontal connected progress stepper matching Reference Panel 3 */}
      <ol className="mx-auto mt-7 grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-4 sm:gap-2">
        {steps.slice(0, 4).map((s, i) => {
          const done = i < step;
          const current = i === step;
          return (
            <li key={s} className="relative flex items-center gap-2.5 sm:flex-col sm:items-center sm:text-center">
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs transition-colors ${
                  done
                    ? "border-safe/60 bg-safe/15 text-safe"
                    : current
                    ? "border-primary bg-primary/20 text-primary shadow-[0_0_16px_-2px_rgba(0,229,255,0.75)]"
                    : "border-border bg-muted/40 text-muted-foreground"
                }`}
              >
                {done ? (
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                ) : current ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
                )}
              </span>
              <span className={`text-xs ${current ? "font-medium text-primary" : done ? "text-foreground" : "text-muted-foreground"}`}>
                {s}
              </span>
            </li>
          );
        })}
      </ol>

      {elapsed > 8 && (
        <p className="mt-5 text-center text-xs text-muted-foreground">
          The free server sleeps when idle and can take up to a minute to wake the first time. Your scan will finish on its own.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 3. Read the verdict aloud (browser speech)                          */
/* ------------------------------------------------------------------ */
export function SpeakVerdict({ isScam, likelihood, category }: { isScam: boolean; likelihood: number; category?: string | null }) {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  useEffect(() => () => { if (supported) window.speechSynthesis.cancel(); }, [supported]);
  if (!supported) return null;

  const pct = Math.round(likelihood * 100);
  const text =
    isScam
        ? `Warning. This is a scam${category ? `, ${category}` : ""}. Scam likelihood ${pct} percent. Do not share any OTP, PIN or money, and report it on 1930.`
        : `This message looks genuine. Scam likelihood is only ${pct} percent. Still, never share your OTP with anyone.`;

  const toggle = () => {
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-IN";
    const voice = synth.getVoices().find((v) => v.lang.toLowerCase().startsWith("en-in"));
    if (voice) u.voice = voice;
    u.rate = 0.95;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    synth.cancel();
    synth.speak(u);
    setSpeaking(true);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex items-center gap-2 border border-border px-3 py-1.5 text-sm hover:bg-muted"
      aria-label={speaking ? "Stop reading" : "Read the verdict aloud"}
    >
      {speaking ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      {speaking ? "Stop" : "Read aloud"}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* 4. Look-alike domain: "paypa1 vs paypal" with the odd letters red   */
/* ------------------------------------------------------------------ */
const BRANDS = [
  "paypal", "amazon", "google", "microsoft", "apple", "netflix", "facebook", "instagram", "whatsapp", "flipkart",
  "paytm", "phonepe", "hdfcbank", "icicibank", "axisbank", "kotak", "onlinesbi", "yonosbi", "irctc", "incometax",
  "uidai", "indiapost", "airtel", "jio", "swiggy", "zomato", "myntra", "meesho", "bescom", "linkedin",
];

function distance(a: string, b: string): number {
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++)
      cur[j] = Math.min((prev[j] ?? 0) + 1, (cur[j - 1] ?? 0) + 1, (prev[j - 1] ?? 0) + (a[i - 1] === b[j - 1] ? 0 : 1));
    prev = cur;
  }
  return prev[b.length] ?? 0;
}

export function findLookalike(hostname: string, backendBrand?: string | null): { fake: string; real: string } | null {
  const parts = hostname.toLowerCase().replace(/^www\./, "").split(/[.-]/).filter((p) => p.length >= 4);
  if (backendBrand) {
    const real = backendBrand.split(".")[0] ?? backendBrand;
    const fake = parts.find((p) => p !== real && distance(p, real) <= 2) ?? parts[0];
    if (fake && fake !== real) return { fake, real };
  }
  for (const p of parts)
    for (const b of BRANDS) if (p !== b && Math.abs(p.length - b.length) <= 1 && distance(p, b) === 1) return { fake: p, real: b };
  return null;
}

export function LookalikeDomain({ hostname, backendBrand }: { hostname: string; backendBrand?: string | null }) {
  const hit = findLookalike(hostname, backendBrand);
  if (!hit) return null;
  const { fake, real } = hit;
  return (
    <div className="mb-4 rounded-xl border border-destructive/40 bg-destructive/5 p-4">
      <p className="text-sm font-medium">Look-alike of a real brand</p>
      <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-lg">
        <span aria-label={`fake: ${fake}`}>
          {fake.split("").map((ch, i) => (
            <span key={i} className={ch !== real[i] ? "rounded bg-destructive/20 px-0.5 font-bold text-destructive" : ""}>{ch}</span>
          ))}
        </span>
        <span className="text-sm text-muted-foreground">pretends to be</span>
        <span className="text-risk-low">{real}</span>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">One or two characters are swapped to fool a quick glance. The real site never uses this address.</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 5. One-tap examples for the demo                                    */
/* ------------------------------------------------------------------ */
export const EXAMPLES: Record<string, { label: string; text: string }[]> = {
  text: [
    { label: "Bank OTP scam", text: "Dear SBI customer, your YONO account will be blocked today due to pending KYC. Share the OTP sent to your mobile and update PAN at http://sbi-yono-kyc.xyz or call 9812345670." },
    { label: "Fake job", text: "Congratulations! You are selected for a part-time job. Earn Rs 5000 daily by liking YouTube videos. Pay Rs 999 registration fee on UPI to start today." },
    { label: "Digital arrest", text: "This is Mumbai Cyber Crime. A parcel with drugs was booked on your Aadhaar. You are under digital arrest. Do not disconnect the video call and transfer Rs 50,000 to the RBI safe account now." },
    { label: "Genuine bank alert", text: "Rs. 2,450.00 debited from A/c XX4821 on 12-10-26 to AMAZON PAY. Not you? Call 1800-1234 (official helpline). Never share your OTP with anyone." },
  ],
  url: [
    { label: "Fake PayPal login", text: "http://paypa1-secure-login.verify-account.top/signin" },
    { label: "Fake SBI KYC", text: "http://sbi-kyc-verify.xyz/login" },
    { label: "Real IRCTC", text: "https://www.irctc.co.in/nget/train-search" },
  ],
  email: [
    {
      label: "Fake HDFC email",
      text: "From: HDFC Bank Alerts <alerts@hdfcbank-secure-verify.com>\nReply-To: support.hdfc.kyc@gmail.com\nSubject: URGENT: Your NetBanking access will be suspended today\nAuthentication-Results: spf=fail dkim=fail\n\nDear Customer, your HDFC NetBanking account will be suspended within 24 hours due to incomplete KYC. Click http://hdfc-netbanking-kyc.top/verify and enter your customer ID, password and the OTP to keep your account active.",
    },
    {
      label: "Genuine Swiggy receipt",
      text: "From: Swiggy <noreply@swiggy.in>\nSubject: Your Swiggy order receipt #458213906\nAuthentication-Results: spf=pass dkim=pass\n\nHi, thanks for ordering with Swiggy. Your order has been delivered. Order total: Rs 412.00, paid using UPI. View your order details anytime in the Swiggy app.",
    },
  ],
};

export function ExampleChips({ channel, onPick, disabled }: { channel: string; onPick: (text: string) => void; disabled?: boolean }) {
  const list = EXAMPLES[channel];
  const ref = useRef<HTMLDivElement>(null);
  if (!list) return null;
  return (
    <div ref={ref} className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground">Try an example:</span>
      {list.map((e) => (
        <button
          key={e.label}
          type="button"
          disabled={disabled}
          onClick={() => onPick(e.text)}
          className="rounded-full border border-border px-3 py-1 text-xs hover:border-primary hover:text-primary disabled:opacity-50"
        >
          {e.label}
        </button>
      ))}
    </div>
  );
}
