"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ShieldAlert } from "lucide-react";

/** Hero illustration: a real-looking scam SMS being "X-rayed" — the trap
 * phrases light up one after another, then the verdict lands. One
 * orchestrated moment on page load; static for reduced-motion users. */
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
  hook: "bg-primary/25 decoration-primary",
  pressure: "bg-risk-medium/25 decoration-risk-medium",
  ask: "bg-destructive/25 decoration-destructive",
  cashout: "bg-risk-high/25 decoration-risk-high",
} as const;
const VAR = { hook: "--primary", pressure: "--risk-medium", ask: "--destructive", cashout: "--risk-high" } as const;

export function HeroXray() {
  const reduce = useReducedMotion();
  let order = 0;
  return (
    <div className="signal-aurora relative rounded-[1.75rem] border border-border bg-card/50 p-5 shadow-2xl backdrop-blur-xl sm:p-7">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>SMS from VK-SBIUPD</span>
        <span>10:42 am</span>
      </div>
      <p className="mt-3 rounded-2xl rounded-tl-sm border border-border bg-background/70 p-4 text-[0.98rem] leading-relaxed">
        {PARTS.map((p, i) => {
          if (!p.stage) return <span key={i}>{p.text}</span>;
          const delay = 0.5 + order++ * 0.45;
          return (
            <motion.mark
              key={i}
              initial={reduce ? false : { backgroundSize: "0% 100%" }}
              animate={{ backgroundSize: "100% 100%" }}
              transition={{ delay, duration: 0.45, ease: "easeOut" }}
              style={{
                backgroundColor: "transparent",
                backgroundImage: `linear-gradient(hsl(var(${VAR[p.stage]}) / .28), hsl(var(${VAR[p.stage]}) / .28))`,
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
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        {PARTS.filter((p) => p.note).map((p, i) => (
          <motion.span
            key={p.note}
            initial={reduce ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 + i * 0.45 }}
            className={`rounded-full border border-border px-2.5 py-1 ${TONE[p.stage!]}`}
          >
            {p.note}
          </motion.span>
        ))}
      </div>
      <motion.div
        initial={reduce ? false : { opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 2.4, duration: 0.35 }}
        className="mt-5 flex items-center gap-3 rounded-2xl border border-destructive/40 bg-destructive/10 p-4"
      >
        <ShieldAlert className="h-7 w-7 text-destructive" />
        <div>
          <p className="font-display text-lg font-semibold leading-tight">Likely scam · fake KYC</p>
          <p className="text-sm text-muted-foreground">97% scam likelihood. Don&apos;t reply, report on Chakshu.</p>
        </div>
      </motion.div>
    </div>
  );
}
