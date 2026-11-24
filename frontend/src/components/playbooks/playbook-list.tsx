"use client";

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  BookOpen,
  Bot,
  ChevronRight,
  FileSearch,
  History,
  MessageSquareText,
  PhoneCall,
  ShieldCheck,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Playbook {
  icon: LucideIcon;
  title: string;
  hint: string;
  steps: string[];
}

const PLAYBOOKS: Playbook[] = [
  {
    icon: MessageSquareText,
    title: "Identify Phishing Attempts",
    hint: "Verify urgent SMS, WhatsApp, or email requests before clicking any link.",
    steps: [
      "Copy the suspicious message or URL directly without opening embedded links.",
      "Inspect it in Scan Tool or Quick Check to detect typosquatted domains and spoofed senders.",
      "Never share OTPs, UPI PINs, or remote screen codes regardless of caller urgency.",
    ],
  },
  {
    icon: PhoneCall,
    title: "Report a Scam Immediately",
    hint: "Act within the Golden Hour to freeze fraudulent transfers.",
    steps: [
      "Call 1930 (National Cybercrime Helpline) immediately if money or credentials were compromised.",
      "Generate a pre-filled incident report directly from a Scam Result card.",
      "File the fraud reference on cybercrime.gov.in and report scam numbers on Chakshu.",
    ],
  },
  {
    icon: Wallet,
    title: "Verify Before Any UPI Payment",
    hint: "Prevent collect-request, fake QR, and spoofed payment screenshot frauds.",
    steps: [
      "Use QR Scanner in Safety Tools to inspect who a QR code actually pays before scanning in your app.",
      "Verify merchant payee names with UPI Pay Check before entering your PIN.",
      "Inspect buyer 'payment successful' screenshots in Payment Proof for fake UTR numbers.",
    ],
  },
  {
    icon: FileSearch,
    title: "Inspect Attachments, PDFs & Voice Calls",
    hint: "Analyze unknown files and digital-arrest call transcripts safely.",
    steps: [
      "Upload suspicious APK/PDF attachments in File Analyzer—nothing is executed or stored.",
      "Paste digital-arrest or courier impersonation transcripts into Voice / SMS Scan.",
      "Inspect Scam X-Ray highlights to spot coercion and urgency triggers.",
    ],
  },
  {
    icon: Bot,
    title: "Use ScamGuard AI Copilot",
    hint: "Get real-time Indian cyber-safety guidance grounded in scan evidence.",
    steps: [
      "Open AI Assistant from the sidebar or bottom-right launcher on any screen.",
      "Ask follow-up questions like 'I shared my UPI details, what should I freeze first?'.",
      "Cross-check unfamiliar tactics directly inside Copilot without storing private chat logs.",
    ],
  },
  {
    icon: History,
    title: "Maintain Audit Records & Reports",
    hint: "Preserve evidence trails for banks, employers, or cyber-cell complaints.",
    steps: [
      "All signed-in scans automatically persist in History with numeric risk scores.",
      "Download formal PDF or CSV reports from any Scan Result.",
      "Track recurrence across malicious phone numbers, links, and UPI IDs in Overview.",
    ],
  },
  {
    icon: TrendingUp,
    title: "Monitor Active Regional Scam Trends",
    hint: "Track emerging phishing campaigns and channel shifts across India.",
    steps: [
      "Review 7-day and 30-day spikes in Scam Trends to spot active bank KYC or reward waves.",
      "Compare source channel distribution between SMS, URL, and Email scams.",
      "Use Playbooks and Safety Tools ahead of major shopping or festive cycles.",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Read Forensic Verdict Signals",
    hint: "Understand Threat Score, TrustLens evidence, and stage breakdown.",
    steps: [
      "Check the verdict tier (Safe, Suspicious, High Risk) and 0–100 Risk Score donut.",
      "Review 'Why it's flagged?' for specific psychological stages and contributing tokens.",
      "Follow prioritized Recommended Actions tailored to the detected channel.",
    ],
  },
];

export function PlaybookList() {
  const reduceMotion = useReducedMotion();
  const [openIdx, setOpenIdx] = useState<Set<number>>(new Set([0]));

  const toggle = (idx: number) => {
    setOpenIdx((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const allOpen = openIdx.size === PLAYBOOKS.length;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="console-kicker mb-2 flex items-center gap-2">
            <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
            Response Playbooks
          </p>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Playbooks</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Step-by-step guides for common scams, emergency response, and verification.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setOpenIdx(allOpen ? new Set() : new Set(PLAYBOOKS.map((_, i) => i)))}
          className="rounded-lg border border-border bg-card/60 px-3.5 py-1.5 text-xs font-medium text-primary transition-colors hover:border-primary/45"
        >
          {allOpen ? "Collapse all" : "Expand all"}
        </button>
      </div>

      {/* Panel 12 sleek expandable rows */}
      <div className="console-panel divide-y divide-border overflow-hidden">
        {PLAYBOOKS.map((pb, idx) => {
          const Icon = pb.icon;
          const isOpen = openIdx.has(idx);
          return (
            <div key={pb.title} className="transition-colors hover:bg-muted/20">
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => toggle(idx)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left sm:px-6"
              >
                <div className="flex min-w-0 items-center gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-primary/35 bg-primary/10 text-primary shadow-[0_0_16px_-6px_rgba(0,229,255,0.45)]">
                    <Icon className="h-4.5 w-4.5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <p className="font-display text-base font-semibold text-foreground">{pb.title}</p>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">{pb.hint}</p>
                  </div>
                </div>
                <ChevronRight
                  className={cn(
                    "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
                    isOpen && "rotate-90 text-primary",
                  )}
                  aria-hidden="true"
                />
              </button>

              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={reduceMotion ? false : { height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <ol className="space-y-2.5 border-t border-border/50 bg-background/35 px-5 py-4 pl-[4.75rem] sm:px-6 sm:pl-[5rem]">
                      {pb.steps.map((step, sIdx) => (
                        <li key={sIdx} className="flex items-start gap-2.5 text-sm leading-relaxed text-foreground/90">
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-primary/35 bg-primary/15 font-mono text-[11px] font-semibold text-primary">
                            {sIdx + 1}
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
}
