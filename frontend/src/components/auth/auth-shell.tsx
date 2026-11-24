"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, ArrowLeft, Globe, MessageSquareWarning, ShieldCheck, Tag } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { ThreatCoreCanvas } from "@/components/visuals/threat-core-canvas";
import { cn } from "@/lib/utils";

const AUTH_TABS = [
  { href: "/login", label: "Sign in" },
  { href: "/register", label: "Create account" },
] as const;

export function AuthShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const reduceMotion = useReducedMotion();
  const isRegister = pathname?.startsWith("/register");

  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,1.14fr)_minmax(0,0.86fr)]">
      {/* Left: Cinematic rotating 3D cybersecurity sphere + Threat Nodes (Reference Panel 02) */}
      <aside className="auth-stage relative isolate hidden overflow-hidden border-r border-border/80 px-10 py-9 lg:flex lg:flex-col lg:justify-between xl:px-14">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(46rem 46rem at 52% 48%, rgba(0, 229, 255, 0.13), transparent 62%), radial-gradient(32rem 32rem at 68% 36%, rgba(139, 92, 246, 0.08), transparent 60%)",
          }}
        />

        <div className="relative z-10 flex items-center justify-between">
          <Link href="/" className="group inline-flex items-center gap-2.5 text-sm font-semibold">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 text-primary shadow-[0_0_20px_-4px_rgba(0,229,255,0.45)] transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <span className="font-display text-lg font-bold tracking-tight text-foreground">
              ScamGuard <span className="text-primary">AI</span>
            </span>
          </Link>

          <span className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1 font-mono text-[11px] font-medium text-primary">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
            Threat Radar Active
          </span>
        </div>

        {/* Centerpiece: large interactive rotating 3D threat sphere with clean perimeter threat pills */}
        <div className="relative mx-auto my-2 flex h-[min(58vh,520px)] w-full max-w-[580px] items-center justify-center">
          <ThreatCoreCanvas mode="auth" threatRatio={0.22} />

          {/* Orbiting Threat Labels (Panel 02 reference) */}
          <div className="pointer-events-none absolute inset-4 hidden xl:block" aria-hidden="true">
            <div className="absolute left-4 top-12 flex items-center gap-2 rounded-xl border border-caution/35 bg-card/85 px-3 py-1.5 text-xs font-medium text-foreground shadow-lg backdrop-blur-md">
              <AlertTriangle className="h-3.5 w-3.5 text-caution" />
              Phishing
            </div>
            <div className="absolute right-6 top-16 flex items-center gap-2 rounded-xl border border-primary/35 bg-card/85 px-3 py-1.5 text-xs font-medium text-foreground shadow-lg backdrop-blur-md">
              <Tag className="h-3.5 w-3.5 text-primary" />
              Fake Offer
            </div>
            <div className="absolute bottom-20 left-2 flex items-center gap-2 rounded-xl border border-violet-400/35 bg-card/85 px-3 py-1.5 text-xs font-medium text-foreground shadow-lg backdrop-blur-md">
              <Globe className="h-3.5 w-3.5 text-violet-400" />
              Malicious Site
            </div>
            <div className="absolute bottom-14 right-4 flex items-center gap-2 rounded-xl border border-destructive/40 bg-card/85 px-3 py-1.5 text-xs font-medium text-foreground shadow-lg backdrop-blur-md">
              <MessageSquareWarning className="h-3.5 w-3.5 text-destructive" />
              Scam SMS
            </div>
          </div>
        </div>

        {/* Minimal editorial signature */}
        <div className="relative z-10 max-w-md space-y-1.5 border-t border-border/60 pt-5">
          <p className="font-display text-lg font-semibold tracking-tight text-foreground">
            Explainable AI defense for messages, links, UPI &amp; voice.
          </p>
          <p className="font-mono text-[11px] tracking-wide text-muted-foreground">
            Zero-storage quick checks · Indian cybercrime helpline 1930
          </p>
        </div>
      </aside>

      {/* Right: Obsidian glass authentication workspace */}
      <div className="flex min-h-screen flex-col bg-background">
        {/* Compact signature sphere preview on mobile viewports */}
        <div className="border-b border-border/80 bg-[#070B14] lg:hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <Link href="/" className="inline-flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 text-primary">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="font-display text-base font-bold tracking-tight text-foreground">
                ScamGuard <span className="text-primary">AI</span>
              </span>
            </Link>
            <ThemeToggle />
          </div>
          <div className="relative h-36 w-full overflow-hidden">
            <ThreatCoreCanvas mode="auth" threatRatio={0.22} />
          </div>
        </div>

        <header className="hidden h-16 items-center justify-between px-8 lg:flex">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Back to home
          </Link>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 items-center justify-center px-4 py-8 sm:px-6 lg:py-10">
          <div className="console-panel w-full max-w-[420px] p-6 sm:p-8">
            {/* Brand mark centered at top of card (Panel 02 reference) */}
            <div className="mb-5 flex items-center justify-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 text-primary shadow-[0_0_16px_-4px_rgba(0,229,255,0.45)]">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="font-display text-base font-bold tracking-tight text-foreground">
                ScamGuard <span className="text-primary">AI</span>
              </span>
            </div>

            {/* Segmented Sign in / Create account switcher */}
            <nav
              aria-label="Authentication mode"
              className="mb-5 grid grid-cols-2 rounded-lg border border-border bg-muted/40 p-1"
            >
              {AUTH_TABS.map((tab) => {
                const active = tab.href === "/register" ? isRegister : !isRegister;
                return (
                  <Link
                    key={tab.href}
                    href={tab.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "relative flex items-center justify-center rounded-md py-1.5 text-xs font-medium transition-colors",
                      active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId={reduceMotion ? undefined : "auth-mode-pill"}
                        transition={{ type: "spring", stiffness: 380, damping: 32 }}
                        className="absolute inset-0 rounded-md border border-primary/35 bg-card shadow-sm"
                        aria-hidden="true"
                      />
                    )}
                    <span className="relative z-10">{tab.label}</span>
                  </Link>
                );
              })}
            </nav>

            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={pathname}
                initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
