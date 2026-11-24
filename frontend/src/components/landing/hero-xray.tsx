"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Radio, ShieldAlert } from "lucide-react";

/** Hero illustration: a real-looking scam SMS being "X-rayed" — the trap
 * phrases light up swiftly in sequence, with the stage chips and verdict
 * immediately legible so the card never appears half-empty. */
const PARTS: Array<{ text: string; stage?: "hook" | "pressure" | "ask" | "cashout"; note?: string }> = [
  { text: "Dear customer, your " },
  { text: "SBI YONO account will be blocked", stage: "pressure", note: "Threat" },
  { text: " " },
  { text: "today", stage: "pressure", note: "Deadline" },
  { text: ". To continue, " },
  { text: "share the OTP", stage: "ask", note: "Asks for OTP" },
  { text: " and update PAN at " },
  { text: "sbi-yono-kyc.xyz", stage: "cashout", note: "Fake site" },
];

const TONE = {
  hook: "bg-primary/20 decoration-primary border-primary/35 text-primary",
  pressure: "bg-risk-medium/20 decoration-risk-medium border-risk-medium/35 text-caution",
  ask: "bg-destructive/20 decoration-destructive border-destructive/35 text-destructive",
  cashout: "bg-risk-high/20 decoration-risk-high border-risk-high/35 text-risk-high",
} as const;
const VAR = { hook: "--primary", pressure: "--risk-medium", ask: "--destructive", cashout: "--risk-high" } as const;

export function HeroXray() {
  const reduce = useReducedMotion();
  let order = 0;
  return (
    <div className="console-panel relative rounded-2xl border border-border/90 bg-card/95 p-5 shadow-2xl backdrop-blur-md sm:p-6">
      <div className="flex items-center justify-between border-b border-border pb-3 font-mono text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5 text-primary">
          <Radio className="h-3.5 w-3.5" aria-hidden="true" />
          INTERCEPTED SIGNAL · X-RAY
        </span>
        <span>SMS · VK-SBIUPD</span>
      </div>

      <p className="mt-4 rounded-xl border border-border bg-background/85 p-4 text-[0.95rem] leading-relaxed text-foreground">
        {PARTS.map((p, i) => {
          if (!p.stage) return <span key={i}>{p.text}</span>;
          const delay = 0.12 + order++ * 0.14;
          return (
            <motion.mark
              key={i}
              initial={reduce ? false : { backgroundSize: "0% 100%" }}
              animate={{ backgroundSize: "100% 100%" }}
              transition={{ delay, duration: 0.3, ease: "easeOut" }}
              style={{
                backgroundColor: "transparent",
                backgroundImage: `linear-gradient(hsl(var(${VAR[p.stage]}) / .26), hsl(var(${VAR[p.stage]}) / .26))`,
                backgroundRepeat: "no-repeat",
              }}
              className={`rounded px-0.5 text-foreground underline decoration-2 underline-offset-4 ${TONE[p.stage].split(" ")[1]}`}
              title={p.note}
            >
              {p.text}
            </motion.mark>
          );
        })}
      </p>

      <div className="mt-3.5 flex flex-wrap gap-1.5 font-mono text-[11px]">
        {PARTS.filter((p) => p.note).map((p, i) => (
          <motion.span
            key={p.note}
            initial={reduce ? false : { opacity: 0.35, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.08, duration: 0.25 }}
            className={`rounded-md border px-2 py-0.5 ${TONE[p.stage!]}`}
          >
            {p.note}
          </motion.span>
        ))}
      </div>

      <motion.div
        initial={reduce ? false : { opacity: 0.4, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.28 }}
        className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-destructive/35 bg-destructive/10 p-3.5"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-destructive/35 bg-destructive/15 text-destructive">
            <ShieldAlert className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="font-display text-base font-semibold leading-tight text-foreground">
              Likely scam · fake KYC
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Do not share OTPs or click. Report on Chakshu.
            </p>
          </div>
        </div>
        <span className="shrink-0 font-mono text-sm font-semibold tabular-nums text-destructive">
          97%
        </span>
      </motion.div>
    </div>
  );
}
