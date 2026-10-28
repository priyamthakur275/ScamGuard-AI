"use client";

import { useState } from "react";
import { PublicShell } from "@/components/layout/public-shell";
import { ErrorBoundary } from "@/components/error-boundary";
import { SimulatorGame } from "@/components/simulator/conversation-simulator";
import { GenuineGame } from "@/components/simulator/genuine-game";
import { cn } from "@/lib/utils";

const MODES = [
  { id: "genuine", label: "Scam → Genuine", blurb: "Fix the traps in a real scam message one by one and watch the live risk score fall until it reads like a genuine message." },
  { id: "chat", label: "Scam conversation", blurb: "Talk to a scripted scammer and choose your replies. Wrong answers show what you would have lost." },
] as const;

export default function SimulatorPage() {
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("genuine");
  const active = MODES.find((m) => m.id === mode)!;
  return (
    <PublicShell>
      <p className="text-xs text-primary">Practice safely</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Scam simulator</h1>
      <div role="tablist" className="mt-5 inline-flex overflow-hidden rounded-lg border border-border text-sm">
        {MODES.map((m) => (
          <button key={m.id} role="tab" aria-selected={mode === m.id} onClick={() => setMode(m.id)}
            className={cn("px-4 py-2", mode === m.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
            {m.label}
          </button>
        ))}
      </div>
      <p className="mt-3 max-w-2xl text-sm text-muted-foreground">{active.blurb}</p>
      <ErrorBoundary area="The simulator">{mode === "genuine" ? <GenuineGame /> : <SimulatorGame />}</ErrorBoundary>
    </PublicShell>
  );
}
