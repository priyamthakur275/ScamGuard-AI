import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      {/* Left: the "signal console" -- dark, monospace, a single scanning
          waveform as the one deliberate moment of motion on this screen. */}
      <div className="auth-blueprint relative hidden overflow-hidden border-r border-border bg-[#101216] px-12 py-10 text-slate-100 lg:flex lg:flex-col lg:justify-between">
        <Link href="/" className="flex items-center gap-2 font-mono text-sm uppercase tracking-[0.14em] text-[#F6F3EA]/70">
          <ShieldAlert className="h-4 w-4 text-cyan-300" />
          ScamGuard
        </Link>

        <div className="flex flex-1 items-center">
          <svg viewBox="0 0 400 120" className="w-full max-w-md" aria-hidden="true">
            <line x1="0" y1="60" x2="400" y2="60" stroke="#F6F3EA" strokeOpacity="0.12" strokeWidth="1" />
            <path
              d="M0,60 L60,60 L75,20 L95,100 L115,60 L400,60"
              fill="none"
              stroke="#E8A33D"
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeDasharray="700"
              strokeDashoffset="700"
              style={{ strokeDashoffset: 0 }}
            />
          </svg>
        </div>

        <div className="max-w-sm">
          <p className="console-kicker mb-3 text-cyan-300">ScamGuard intelligence</p>
          <p className="text-2xl font-semibold leading-tight text-slate-100">See the signal. Understand the threat.</p>
          <p className="mt-4 text-sm leading-6 text-slate-400">A focused workspace for multimodal scam detection, evidence, and response.</p>
        </div>
      </div>

      {/* Right: the actual access-request form, on a paper surface. */}
      <div className="flex flex-col bg-background">
        <header className="flex h-16 items-center justify-between px-6 lg:justify-end">
          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <ShieldAlert className="h-5 w-5 text-primary" />
            <span className="font-mono text-sm font-medium uppercase tracking-wide">ScamGuard</span>
          </Link>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 items-center justify-center px-4 py-12">
          <div className="w-full max-w-md border border-border bg-card/90 p-8 rounded-xl shadow-sm">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
