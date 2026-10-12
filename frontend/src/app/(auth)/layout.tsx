import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { BackendWarmup } from "@/components/layout/backend-warmup";
import { HeroXray } from "@/components/landing/hero-xray";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <BackendWarmup />
      {/* Left: the same X-Ray moment as the landing page, so signing in
          feels like part of one product. */}
      <div className="relative isolate hidden overflow-hidden border-r border-border px-12 py-10 lg:flex lg:flex-col lg:justify-between">
        <div aria-hidden="true" className="hero-glow" />
        <Link href="/" className="flex items-center gap-2 text-sm font-medium">
          <ShieldAlert className="h-5 w-5 text-primary" />
          ScamGuard
        </Link>
        <div className="my-10 max-w-lg">
          <HeroXray />
        </div>
        <div className="max-w-sm">
          <p className="font-display text-2xl font-bold leading-tight">Every flagged message comes with the reason.</p>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Your scans, history and reports stay in your account. Lost money? Call 1930 first.
          </p>
        </div>
      </div>

      {/* Right: the actual access-request form, on a paper surface. */}
      <div className="flex flex-col bg-background">
        <header className="flex h-16 items-center justify-between px-6 lg:justify-end">
          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <ShieldAlert className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium">ScamGuard</span>
          </Link>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 items-center justify-center px-4 py-12">
          <div className="sg-card w-full max-w-md border border-border p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
