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
  ScanSearch,
  ShieldAlert,
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

const BENCHMARKS = [
  { value: "97.5%", label: "Campaign-Held-Out F1", sub: "1,874 real Indian messages" },
  { value: "97.2%", label: "Evasion Recall", sub: "Homoglyphs, leetspeak & defanged URLs" },
  { value: "0.67 ms", label: "CPU Latency", sub: "Real-time scoring per message" },
  { value: "885+", label: "Automated Tests", sub: "Backend, ML & Frontend CI" },
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
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/35 bg-primary/10">
            <ShieldAlert className="h-4.5 w-4.5 text-primary" />
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-foreground">ScamGuard</span>
        </Link>
        <nav className="flex items-center gap-3 md:gap-5">
          <Link href="/#quick-check" className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground lg:inline">
            Quick check
          </Link>
          <Link href="/tools" className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground md:inline">
            Safety tools
          </Link>
          <Link href="/trends" className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground md:inline">
            Scam trends
          </Link>
          <InstallAppButton />
          <ThemeToggle />
          <Link href="/login" className="whitespace-nowrap text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Sign in
          </Link>
          <Button onClick={() => router.push("/register")} size="sm" className="hidden sm:inline-flex">
            Get started
          </Button>
        </nav>
      </header>

      <main className="relative isolate flex-1 overflow-x-clip">
        {/* Hero Command Showcase */}
        <section className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 py-14 lg:grid-cols-[1.08fr_0.92fr] lg:py-20">
          <motion.div
            className="flex flex-col items-start text-left"
            initial={false}
            animate="visible"
            variants={containerVariants}
          >
            <motion.div
              variants={itemVariants}
              className="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1 font-mono text-[11px] font-medium text-primary"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-risk-low" aria-hidden="true" />
              AI Threat Intelligence · Zero-Storage Quick Check
            </motion.div>

            <motion.h1
              variants={itemVariants}
              className="mb-5 max-w-2xl font-display text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-[3.35rem]"
            >
              Forward the message.{" "}
              <span className="text-signal">We&apos;ll show you the trap.</span>
            </motion.h1>

            <motion.p
              variants={itemVariants}
              className="mb-8 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg"
            >
              ScamGuard analyzes SMS, WhatsApp chats, links, emails, screenshots, and calls in milliseconds—pinpointing
              the exact psychological and technical triggers behind Indian digital fraud.
            </motion.p>

            <motion.div variants={itemVariants} className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
              <Button
                size="lg"
                className="h-12 px-7 text-sm font-semibold sm:h-14 sm:text-base"
                onClick={() => document.getElementById("quick-check")?.scrollIntoView({ behavior: "smooth" })}
              >
                Check a message now
                <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="h-12 px-7 text-sm font-medium sm:h-14 sm:text-base"
                onClick={() => router.push("/login")}
              >
                Open workspace / Demo
              </Button>
            </motion.div>
            <motion.p variants={itemVariants} className="mt-4 font-mono text-xs text-muted-foreground">
              No sign-up needed for quick check · Nothing you paste is stored.
            </motion.p>
          </motion.div>

          {/* Custom 3D Neural Core + Intercepted Signal X-Ray */}
          <div className="relative flex flex-col items-center">
            <div className="relative flex h-[210px] w-full items-center justify-center sm:h-[235px]">
              <ThreatCoreCanvas mode="hero" threatRatio={0.22} />
              <div className="pointer-events-none absolute inset-x-0 bottom-2 flex justify-center">
                <span className="rounded-full border border-primary/25 bg-background/85 px-3 py-0.5 font-mono text-[10px] tracking-wider text-primary backdrop-blur">
                  NEURAL + INTENT ENGINE · DE-OBFUSCATION ACTIVE
                </span>
              </div>
            </div>
            <div className="-mt-3 w-full">
              <HeroXray />
            </div>
          </div>
        </section>

        {/* Verified Benchmark Telemetry Strip */}
        <section aria-label="Verified model benchmarks" className="border-y border-border bg-card/55">
          <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-y divide-border sm:grid-cols-4 sm:divide-y-0">
            {BENCHMARKS.map((item) => (
              <div key={item.label} className="px-6 py-5 transition-colors hover:bg-muted/30">
                <p className="font-mono text-2xl font-semibold tabular-nums tracking-tight text-foreground sm:text-[1.75rem]">
                  {item.value}
                </p>
                <p className="mt-1 text-xs font-semibold text-primary">{item.label}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{item.sub}</p>
              </div>
            ))}
          </div>
        </section>

        <QuickCheck />
        <HowToCards />

        {/* Feature Capabilities Grid */}
        <section className="border-t border-border bg-card/25 px-6 py-20">
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
                    <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
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
            <ShieldAlert className="h-4 w-4 text-primary" aria-hidden="true" />
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
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
