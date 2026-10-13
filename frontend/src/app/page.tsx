"use client";

import Link from "next/link";
import { InstallAppButton } from "@/components/layout/install-app-button";
import { HeroXray } from "@/components/landing/hero-xray";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Lock, ScanSearch, ShieldAlert, Sparkles, CheckCircle2, MessageCircleQuestion, FileOutput } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { BackendWarmup } from "@/components/layout/backend-warmup";
import { QuickCheck } from "@/components/landing/quick-check";
import { FullPageSpinner } from "@/components/ui/spinner";
import { motion, Variants } from "framer-motion";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Scam X-Ray",
    description: "See the exact words that make a message a scam, and how it works: the hook, the pressure, what they want, how money leaves.",
  },
  {
    icon: Sparkles,
    title: "Any format, one check",
    description: "SMS and WhatsApp text, links, emails, chat screenshots, PDFs, QR codes and phone calls, in English, Hindi or Hinglish.",
  },
  {
    icon: Lock,
    title: "Website trust score",
    description: "How old a domain is, where a link really lands, and whether the page asks for passwords, OTPs or card details.",
  },
  {
    icon: MessageCircleQuestion,
    title: "Ask ScamGuard",
    description: "\u201cI already paid, what now?\u201d Plain answers grounded in the scan, including the exact steps to take.",
  },
  {
    icon: ShieldAlert,
    title: "Family guardian",
    description: "Link a parent or grandparent. When they check a likely scam, you see it and can call before money is sent.",
  },
  {
    icon: FileOutput,
    title: "Report in one tap",
    description: "Chakshu for scam numbers, 1930 and cybercrime.gov.in for lost money, with the complaint already written for you.",
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
      <BackendWarmup />
      <header className="sticky top-0 z-50 flex h-[4.5rem] items-center justify-between border-b border-border bg-background/90 px-6 backdrop-blur-xl md:px-10">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center border border-primary/30 bg-primary/10">
            <ShieldAlert className="h-5 w-5 text-primary" />
          </div>
          <div><span className="text-lg font-semibold tracking-tight">ScamGuard</span></div>
        </div>
        <div className="flex items-center gap-4">
          <InstallAppButton />
          <LanguageToggle />
          <Link href="/trends" className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground md:inline">Scam trends</Link>
          <Link href="/trainer" className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground md:inline">Trainer</Link>
          <Link href="/test-bench" className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground md:inline">Test bench</Link>
          <ThemeToggle />
          <Link href="/login" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Sign in
          </Link>
          <Button onClick={() => router.push("/register")} size="sm" className="hidden sm:flex">
            Get started
          </Button>
        </div>
      </header>

      <main className="relative isolate flex-1 overflow-hidden">
        <div aria-hidden="true" className="hero-glow" />
        {/* Hero Section */}
        <section className="relative mx-auto grid max-w-6xl items-center gap-14 px-6 py-16 lg:grid-cols-[1.1fr_1fr] lg:py-24">
          <motion.div
            className="flex flex-col items-start text-left"
            initial={false}
            animate="visible"
            variants={containerVariants}
          >
            <motion.h1
              variants={itemVariants}
              className="mb-6 max-w-3xl font-display text-5xl font-extrabold leading-[1.02] tracking-[-0.04em] sm:text-6xl xl:text-[4.6rem]"
            >
              Forward the message. We&apos;ll show you the trap.
            </motion.h1>

            <motion.p
              variants={itemVariants}
              className="mb-9 max-w-xl text-lg leading-relaxed text-muted-foreground"
            >
              ScamGuard reads SMS, WhatsApp chats, links, emails, screenshots and calls, and points to the exact words
              that make them a scam — in English or Hindi.
            </motion.p>

            <motion.div variants={itemVariants} className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
              <Button size="lg" className="h-14 px-8 text-base" onClick={() => document.getElementById("quick-check")?.scrollIntoView({ behavior: "smooth" })}>
                Check a message now
              </Button>
              <Button size="lg" variant="outline" className="h-14 px-8 text-base" onClick={() => router.push("/register")}>
                Create free account
              </Button>
            </motion.div>
            <motion.p variants={itemVariants} className="mt-5 text-sm text-muted-foreground">
              No sign-up needed for a quick check. Nothing you paste is stored.
            </motion.p>
          </motion.div>
          <HeroXray />
        </section>

        <QuickCheck />

        {/* Feature Section */}
        <section className="border-t border-border bg-card/30 px-6 py-20">
          <div className="mx-auto max-w-6xl">
            <div className="mb-16 max-w-2xl">
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Everything you need when a message feels wrong
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
              <h2 className="font-display text-3xl font-bold sm:text-4xl">Your messages stay yours.</h2>
              <p className="text-lg text-muted-foreground">
                Quick checks are never saved. Saved scans are visible only to you, and to a family member only if you choose. Links are opened on our server, never on your phone.
              </p>
            </div>
            <div>
              <ul className="grid gap-3 text-left sm:grid-cols-2">
                {[
                  "Quick checks are never saved",
                  "Only you see your scans",
                  "Links opened safely on our server",
                  "Download or delete everything",
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
            <Link href="/trends" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Scam trends</Link>
            <Link href="/trainer" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Scam trainer</Link>
            <Link href="/test-bench" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Test bench</Link>
            <Link href="/extension" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Browser extension</Link>
            <Link href="/register" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Create account</Link>
            <Link href="/login" className="text-sm text-muted-foreground transition-colors hover:text-foreground">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
