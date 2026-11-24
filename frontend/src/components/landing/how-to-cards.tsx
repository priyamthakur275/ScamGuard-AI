"use client";

import { useState } from "react";
import { BookOpen, Bot, FileSearch, History, MessageSquareText, PhoneCall, ShieldCheck, TrendingUp, Wallet, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type Card = { icon: LucideIcon; title: string; hint: string; steps: string[] };

const CARDS: Card[] = [
    { icon: MessageSquareText, title: "Check a message", hint: "SMS, WhatsApp or email text", steps: ["Copy the message you received.", "Paste it in the quick check box on this page.", "Press Check message. No sign-up needed."] },
    { icon: ShieldCheck, title: "Read the result", hint: "Scam or genuine, and why", steps: ["The top line says Scam or Looks genuine.", "Red phrases are the traps, grouped by stage.", "TrustLens shows the evidence for and against."] },
    { icon: FileSearch, title: "Links, screenshots, calls", hint: "More than plain text", steps: ["Create a free account or use the demo account.", "Open Investigate and pick a tab, like URL, Screenshot or Voice.", "Upload or paste, then press Analyze evidence."] },
    { icon: Wallet, title: "Before you pay", hint: "Safety tools, no login", steps: ["Open Safety tools from the top menu.", "Scan a QR to see who really gets paid.", "Check a UPI request or a payment screenshot."] },
    { icon: Bot, title: "Ask Copilot", hint: "The robot at the bottom right", steps: ["Tap the robot button on any page.", "Paste a message, or ask 'is this real?'.", "Ask follow-ups like 'I already paid, what now?'."] },
    { icon: PhoneCall, title: "Already paid?", hint: "Act within the first hour", steps: ["Call 1930, the free cyber helpline, at once.", "On a scam result, tap 'I already paid' for a ready complaint.", "Report the number on Chakshu (sancharsaathi.gov.in)."] },
    { icon: TrendingUp, title: "Scam trends", hint: "What is going around", steps: ["Open Scam trends from the top menu.", "See the scam types flagged most this month.", "Learn the warning signs with Flashcards."] },
    { icon: History, title: "Keep a record", hint: "History and reports", steps: ["Signed-in scans are saved in History.", "Download a PDF or CSV report of any scan.", "Analytics shows your scans over time."] },
  ];

function FlipCard({ card, n, flipped, onFlip }: { card: Card; n: number; flipped: boolean; onFlip: () => void }) {
  const Icon = card.icon;
  return (
    <button
      type="button"
      onClick={onFlip}
      aria-pressed={flipped}
      aria-label={`${card.title}: ${flipped ? "hide steps" : "show steps"}`}
      className="group h-44 w-full sm:h-56 text-left [perspective:1000px] focus-visible:outline-none"
    >
      <div className={cn("relative h-full w-full rounded-xl transition-transform duration-500 [transform-style:preserve-3d] motion-reduce:transition-none", flipped && "[transform:rotateY(180deg)]")}>
        {/* front */}
        <div className="console-panel absolute inset-0 flex flex-col justify-between p-5 [backface-visibility:hidden] group-hover:border-primary/50 group-focus-visible:ring-2 group-focus-visible:ring-primary">
          <div className="flex items-start justify-between">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary"><Icon className="h-5 w-5" /></span>
            <span className="font-mono text-xs tabular-nums text-muted-foreground">{String(n).padStart(2, "0")}</span>
          </div>
          <div>
            <p className="font-display text-base font-semibold text-foreground">{card.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{card.hint}</p>
          </div>
        </div>
        {/* back */}
        <div className="console-panel absolute inset-0 border-primary/40 p-5 [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <p className="font-display text-sm font-semibold text-primary">{card.title}</p>
          <ol className="mt-3 space-y-2">
            {card.steps.map((s, i) => (
              <li key={i} className="flex gap-2.5 text-[13px] leading-snug text-foreground">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-primary/40 bg-primary/15 font-mono text-[11px] font-semibold text-primary">{i + 1}</span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </button>
  );
}

/** "How to use ScamGuard": eight flip cards, each with three short steps. */
export function HowToCards() {
  const cards = CARDS;
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (i: number) => setOpen((o) => { const n = new Set(o); if (n.has(i)) n.delete(i); else n.add(i); return n; });
  const allOpen = open.size === cards.length;
  return (
    <section id="how-to-use" className="scroll-mt-20 border-t border-border px-6 py-16">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="console-kicker flex items-center gap-2"><BookOpen className="h-3.5 w-3.5" /> Interactive Playbooks</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Everything it does, in three steps each</h2>
            <p className="mt-1.5 text-sm text-muted-foreground">Select a playbook card to flip and reveal the workflow.</p>
          </div>
          <button type="button" onClick={() => setOpen(allOpen ? new Set() : new Set(cards.map((_, i) => i)))} className="text-sm font-medium text-primary hover:underline">
            {allOpen ? "Flip all back" : "Show all steps"}
          </button>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c, i) => <FlipCard key={c.title} card={c} n={i + 1} flipped={open.has(i)} onFlip={() => toggle(i)} />)}
        </div>
      </div>
    </section>
  );
}
