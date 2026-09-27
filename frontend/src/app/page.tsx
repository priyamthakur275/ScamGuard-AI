"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Lock, ScanSearch, ShieldAlert, Sparkles, Zap, ShieldCheck, CheckCircle2, ArrowRight, Mail, FolderKanban, MessageCircleQuestion, FlaskConical, FileOutput } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { FullPageSpinner } from "@/components/ui/spinner";
import { motion, Variants } from "framer-motion";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Multimodal Scanning",
    description: "Analyze text, URLs, email, images/OCR, PDFs, QR codes, live camera, and voice through one unified pipeline.",
  },
  {
    icon: Sparkles,
    title: "Explainable Risk Analysis",
    description: "Understand the contributing signals, confidence, and risk behind each verdict.",
  },
  {
    icon: Lock,
    title: "URL & Domain Intelligence",
    description: "Inspect lookalike domains, hidden destinations, suspicious URL structures, and available redirect evidence.",
  },
  {
    icon: Mail,
    title: "Email Forensics",
    description: "Inspect senders, reply addresses, attachments, and claimed authentication headers in one evidence view.",
  },
  {
    icon: ShieldAlert,
    title: "Entity & Threat Correlation",
    description: "Connect recurring phone numbers, domains, payment identifiers, and other entities across your saved scans.",
  },
  {
    icon: FolderKanban,
    title: "Investigation Cases",
    description: "Group related scans into a case with a real action-driven timeline, notes, and aggregated evidence.",
  },
  {
    icon: MessageCircleQuestion,
    title: "Evidence-Grounded Copilot",
    description: "Ask targeted questions about a finding and get answers grounded in its observed evidence.",
  },
  {
    icon: FlaskConical,
    title: "Robustness Evaluation",
    description: "Controlled text transforms (case, spelling, homoglyphs, obfuscation) run through the real model to measure actual prediction stability.",
  },
  {
    icon: FileOutput,
    title: "Exportable Reports",
    description: "JSON, CSV, and PDF reports for any scan or case, built from one shared data source so every format stays consistent.",
  },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.24, ease: "easeOut" }
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
      <header className="sticky top-0 z-50 flex h-[4.5rem] items-center justify-between border-b border-border bg-background/90 px-6 backdrop-blur-xl md:px-10">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center border border-primary/30 bg-primary/10">
            <ShieldAlert className="h-5 w-5 text-primary" />
          </div>
          <div><span className="text-lg font-semibold tracking-tight">ScamGuard</span><span className="ml-2 hidden font-mono text-[10px] uppercase tracking-[0.16em] text-primary sm:inline">Threat intelligence</span></div>
        </div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Link href="/login" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Sign in
          </Link>
          <Button onClick={() => router.push("/register")} size="sm" className="hidden sm:flex">
            Get started
          </Button>
        </div>
      </header>

      <main className="flex-1 overflow-hidden">
        {/* Hero Section */}
        <section className="relative mx-auto grid max-w-6xl items-center gap-14 px-6 py-20 lg:grid-cols-[1.15fr_1fr] lg:py-28">
          <motion.div
            className="flex flex-col items-start text-left"
            initial={false}
            animate="visible"
            variants={containerVariants}
          >
            <motion.div variants={itemVariants} className="console-kicker mb-6 inline-flex items-center gap-2">
              <Zap className="h-3.5 w-3.5" />
              AI-powered scam detection & threat intelligence
            </motion.div>

            <motion.h1
              variants={itemVariants}
              className="mb-8 max-w-5xl text-5xl font-semibold leading-[1.05] tracking-[-0.045em] sm:text-6xl xl:text-7xl"
            >
              A suspicious message.<br />
              <span className="text-muted-foreground">A clearer decision.</span>
            </motion.h1>

            <motion.p
              variants={itemVariants}
              className="mb-10 max-w-xl text-lg leading-relaxed text-muted-foreground"
            >
              Investigate suspicious messages, links, and documents. Follow the evidence from first signal to a decision you can explain.
            </motion.p>

            <motion.div variants={itemVariants} className="flex w-full flex-col gap-4 sm:w-auto sm:flex-row">
              <Button size="lg" className="h-14 px-8 text-base" onClick={() => router.push("/register")}>
                Start investigating
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              <Button size="lg" variant="outline" className="h-14 px-8 text-base" onClick={() => router.push("/login")}>
                Sign in
              </Button>
            </motion.div>
          </motion.div>
          <div className="landing-workflow rounded-lg border border-border bg-card p-6 shadow-sm md:p-8">
            <div className="flex items-center justify-between border-b border-border pb-5"><span className="console-kicker">The investigation workflow</span><ScanSearch className="h-5 w-5 text-primary" /></div>
            <div className="mt-6 flex flex-wrap gap-2">{["Message", "URL", "Email", "Image", "PDF", "QR", "Voice"].map(label => <span key={label} className="rounded-md border border-border bg-muted/50 px-3 py-2 font-mono text-xs">{label}</span>)}</div>
            <ol className="mt-7 space-y-0">{[
              ["01", "Gather the evidence", "Extract text and identify relevant entities."],
              ["02", "Understand the risk", "Review model signals and available intelligence."],
              ["03", "Take the next step", "Open a case, ask Copilot, or export a report."],
            ].map(([number, title, detail]) => <li key={number} className="flex gap-4 border-b border-border py-5 last:border-0"><span className="font-mono text-xs text-primary">{number}</span><div><h2 className="text-sm font-semibold">{title}</h2><p className="mt-1 text-sm leading-6 text-muted-foreground">{detail}</p></div></li>)}</ol>
            <p className="mt-4 border-t border-border pt-4 text-xs text-muted-foreground">One investigation workspace. Evidence behind every verdict.</p>
          </div>
        </section>

        {/* Feature Section */}
        <section className="border-t border-border bg-card/30 px-6 py-20">
          <div className="mx-auto max-w-6xl">
            <div className="mb-16 max-w-2xl">
              <p className="mb-2 font-mono text-xs uppercase tracking-wide text-muted-foreground">How it works</p>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                A single surface for the whole investigation
              </h2>
            </div>

            <motion.div
              className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-3"
              initial={false}
              animate="visible"
              viewport={{ once: true, margin: "-100px" }}
              variants={containerVariants}
            >
              {FEATURES.map(({ icon: Icon, title, description }) => (
                <motion.div key={title} variants={itemVariants}>
                  <Card className="h-full rounded-none border-0 bg-card p-7 shadow-none transition-colors hover:bg-muted">
                    <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
                    <p className="leading-relaxed text-muted-foreground">{description}</p>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* Security Section */}
        <section className="px-6 py-24">
          <motion.div
            className="mx-auto grid max-w-6xl gap-10 rounded-lg border border-border bg-card p-8 md:p-12 lg:grid-cols-[1fr_1fr] lg:items-center"
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
          >
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-sm border border-[hsl(var(--risk-low))]/30 bg-[hsl(var(--risk-low))]/10 px-3 py-1 font-mono text-xs uppercase tracking-wide text-[hsl(var(--risk-low))]">
                <ShieldCheck className="h-3.5 w-3.5" />
                Security
              </div>
              <h2 className="font-sans text-3xl font-semibold sm:text-4xl">An investigation stays yours.</h2>
              <p className="text-lg text-muted-foreground">
                Account access controls and protected analysis endpoints support your investigation. Review the model evaluation before relying on its predictions.
              </p>
            </div>
            <div>
              <ul className="grid gap-3 text-left sm:grid-cols-2">
                {[
                  "Bcrypt password hashing",
                  "Short-lived JWTs + refresh rotation",
                  "SSRF-hardened URL analysis",
                  "CAPTCHA on registration & abuse",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2 rounded-md border border-border bg-background px-4 py-3 text-sm font-medium text-foreground">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </section>
      </main>

      <footer className="border-t border-border bg-background px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 md:flex-row">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-medium text-muted-foreground">ScamGuard © 2026</span>
          </div>
          <p className="text-center text-sm text-muted-foreground md:text-left">
            AI-powered scam detection & threat intelligence.
          </p>
          <div className="flex gap-4">
            <Link href="/register" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Create account</Link>
            <Link href="/login" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
