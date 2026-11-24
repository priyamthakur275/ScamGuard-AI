"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  FileOutput,
  Lock,
  MessageCircleQuestion,
  Play,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { motion, Variants } from "framer-motion";
import { InstallAppButton } from "@/components/layout/install-app-button";
import { HeroXray } from "@/components/landing/hero-xray";
import { ThreatCoreCanvas } from "@/components/visuals/threat-core-canvas";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { BackendWarmup } from "@/components/layout/backend-warmup";
import { QuickCheck } from "@/components/landing/quick-check";
import { HowToCards } from "@/components/landing/how-to-cards";
import { FullPageSpinner } from "@/components/ui/spinner";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Scam X-Ray",
    description:
      "See the exact words that make a message a scam, mapped to four stages: the hook, the pressure, what they ask for, and how money leaves.",
  },
  {
    icon: Sparkles,
    title: "Any format, one check",
    description:
      "SMS and WhatsApp text, links, emails, chat screenshots, PDFs, QR codes, and call transcripts analyzed in one unified pipeline.",
  },
  {
    icon: Lock,
    title: "Website trust score",
    description:
      "Checks domain age, redirects, TLS metadata, lookalike typosquatting, and whether a page captures passwords, OTPs, or card details.",
  },
  {
    icon: MessageCircleQuestion,
    title: "Ask ScamGuard Copilot",
    description:
      "“I already paid, what now?” Plain, evidence-grounded answers tied directly to your scan and Indian cyber-safety playbooks.",
  },
  {
    icon: ShieldAlert,
    title: "Golden Hour help",
    description:
      "Already paid or shared an OTP? Activates a one-hour countdown, direct 1930 helpline dialer, and a pre-filled complaint.",
  },
  {
    icon: FileOutput,
    title: "Report in one tap",
    description:
      "Chakshu for scam numbers and links, 1930 and cybercrime.gov.in for financial fraud, with ready-to-paste incident details.",
  },
];

const HERO_STATS = [
  { value: "97.5%", label: "Campaign-Held-Out F1" },
  { value: "97.2%", label: "Evasion Recall" },
  { value: "0.67 ms", label: "Scoring Latency" },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.28, ease: "easeOut" },
  },
};

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) return <FullPageSpinner />;
  if (isAuthenticated) return null;

  return (
    <div className="flex min-h-screen flex-col">
      <BackendWarmup />
      <header className="sticky top-0 z-50 flex h-[4.25rem] items-center justify-between border-b border-border bg-background/85 px-5 backdrop-blur-xl md:px-10">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 shadow-[0_0_18px_-4px_rgba(0,229,255,0.45)]">
            <ShieldCheck className="h-4.5 w-4.5 text-primary" />
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-foreground">
            ScamGuard <span className="text-primary">AI</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm md:flex">
          <Link href="/" className="relative py-1 font-medium text-primary after:absolute after:inset-x-0 after:-bottom-0.5 after:h-0.5 after:rounded-full after:bg-primary">
            Home
          </Link>
          <Link href="/#features" className="text-muted-foreground transition-colors hover:text-foreground">
            Features
          </Link>
          <Link href="/tools" className="text-muted-foreground transition-colors hover:text-foreground">
            Safety tools
          </Link>
          <Link href="/trends" className="text-muted-foreground transition-colors hover:text-foreground">
            Insights
          </Link>
          <Link href="/cross-domain" className="text-muted-foreground transition-colors hover:text-foreground">
            Research
          </Link>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <InstallAppButton />
          <ThemeToggle />
          <Link
            href="/login"
            className="whitespace-nowrap rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-muted/60 sm:px-3.5 sm:text-sm"
          >
            Log In
          </Link>
          <Button onClick={() => router.push("/register")} size="sm" className="px-2.5 text-xs sm:px-3.5 sm:text-sm">
            Get Started
          </Button>
        </div>
      </header>

      <main className="relative isolate flex-1 overflow-x-clip">
        {/* Reference Panel 1: Cinematic Hero with Large 3D Shield-Globe Centerpiece */}
        <section className="relative mx-auto grid max-w-6xl items-center gap-10 px-6 pb-16 pt-12 lg:min-h-[calc(100vh-4.25rem)] lg:grid-cols-[1.05fr_0.95fr] lg:py-20">
          <motion.div
            className="flex flex-col items-start text-left"
            initial={false}
            animate="visible"
            variants={containerVariants}
          >
            <motion.div
              variants={itemVariants}
              className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/35 bg-primary/10 px-3.5 py-1 text-xs font-medium text-primary"
            >
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              AI-Powered Scam Protection
            </motion.div>

            <motion.h1
              variants={itemVariants}
              className="mb-5 max-w-2xl font-display text-4xl font-bold leading-[1.06] tracking-tight sm:text-5xl lg:text-[3.65rem]"
            >
              Stay One Step <span className="text-signal">Ahead of Scams</span>
            </motion.h1>

            <motion.p
              variants={itemVariants}
              className="mb-8 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg"
            >
              Detect, analyze, and stop online threats in real time with AI, threat intelligence, and fraud analytics.
            </motion.p>

            <motion.div variants={itemVariants} className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
              <Button
                size="lg"
                className="h-12 px-7 text-sm font-semibold sm:h-14 sm:text-base"
                onClick={() => document.getElementById("quick-check")?.scrollIntoView({ behavior: "smooth" })}
              >
                Scan Now
                <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="h-12 px-7 text-sm font-medium sm:h-14 sm:text-base"
                onClick={() => router.push("/login")}
              >
                <Play className="mr-1.5 h-3.5 w-3.5 fill-current text-primary" aria-hidden="true" />
                Try Demo
              </Button>
            </motion.div>

            {/* Real Verified Model Telemetry Row (from results_v2.md) */}
            <motion.div
              variants={itemVariants}
              className="mt-10 grid w-full max-w-lg grid-cols-3 gap-6 border-t border-border/80 pt-6"
            >
              {HERO_STATS.map((s) => (
                <div key={s.label}>
                  <p className="font-display text-2xl font-bold tabular-nums tracking-tight text-foreground sm:text-3xl">
                    {s.value}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{s.label}</p>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Dominant 3D Holographic Shield + Neural Globe + Flowing Cyan Wave */}
          <div className="relative flex h-[340px] w-full items-center justify-center sm:h-[430px] lg:h-[470px]">
            <ThreatCoreCanvas mode="hero" threatRatio={0} />
          </div>
        </section>

        {/* Live Signal X-Ray Showcase */}
        <section className="border-t border-border bg-card/30 px-6 py-14">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="console-kicker mb-2">Explainable Detection</p>
              <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
                Every flagged message reveals why it&apos;s a trap.
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                Instead of an opaque score, ScamGuard dissects incoming messages into psychological stages—urgency
                pressure, credential asks, and suspicious cash-out domains—so anyone can spot the scam immediately.
              </p>
            </div>
            <HeroXray />
          </div>
        </section>

        <QuickCheck />
        <HowToCards />

        {/* Feature Capabilities Grid */}
        <section id="features" className="scroll-mt-20 border-t border-border bg-card/25 px-6 py-20">
          <div className="mx-auto max-w-6xl">
            <div className="mb-12 max-w-2xl">
              <p className="console-kicker mb-2">Defense Capabilities</p>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Everything you need when a message feels wrong
              </h2>
            </div>

            <motion.div
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
              initial={false}
              whileInView="visible"
              viewport={{ once: true, amount: 0.12 }}
              variants={containerVariants}
            >
              {FEATURES.map(({ icon: Icon, title, description }) => (
                <motion.div key={title} variants={itemVariants}>
                  <Card className="console-panel h-full p-6">
                    <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-primary/30 bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* Privacy & Server Isolation Architecture */}
        <section className="border-t border-border px-6 py-20">
          <motion.div
            className="console-panel mx-auto grid max-w-6xl gap-10 p-8 md:p-12 lg:grid-cols-[1fr_1fr] lg:items-center"
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.35 }}
          >
            <div className="space-y-4">
              <p className="console-kicker">Privacy by Architecture</p>
              <h2 className="font-display text-3xl font-bold sm:text-4xl">Your messages stay yours.</h2>
              <p className="text-base leading-relaxed text-muted-foreground">
                Quick checks are processed in memory and discarded. Saved workspace scans stay strictly scoped to your
                account, and suspicious links are inspected server-side with SSRF protections—never from your browser.
              </p>
            </div>
            <div>
              <ul className="grid gap-3 text-left sm:grid-cols-2">
                {[
                  "Quick checks are never stored",
                  "Scans visible only to your account",
                  "Links fetched safely on server",
                  "Export or delete anytime",
                ].map((item) => (
                  <li
                    key={item}
                    className="flex items-center gap-2.5 rounded-lg border border-border bg-background/70 px-4 py-3 text-sm font-medium text-foreground"
                  >
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-safe" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </section>
      </main>

      <footer className="border-t border-border bg-background px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-5 md:flex-row">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" aria-hidden="true" />
            <span className="text-sm font-medium text-muted-foreground">ScamGuard AI · 2026</span>
          </div>
          <p className="text-center text-xs text-muted-foreground">
            Lost money to a scam? Call <a href="tel:1930" className="font-semibold text-foreground underline">1930</a> or report at{" "}
            <a href="https://cybercrime.gov.in/" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">
              cybercrime.gov.in
            </a>.
          </p>
          <div className="flex gap-5 text-sm">
            <Link href="/extension" className="text-muted-foreground transition-colors hover:text-foreground">
              Extension
            </Link>
            <Link href="/register" className="text-muted-foreground transition-colors hover:text-foreground">
              Create account
            </Link>
            <Link href="/login" className="text-muted-foreground transition-colors hover:text-foreground">
              Log in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
