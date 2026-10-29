"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { InstallAppButton } from "@/components/layout/install-app-button";
import { ElderToggle } from "@/components/analysis/protect-features";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { useLanguage } from "@/lib/i18n/language-context";
import type { StringKey } from "@/lib/i18n/strings";

const NAV: { href: string; label: StringKey }[] = [
  { href: "/#quick-check", label: "nav.quick" },
  { href: "/flashcards", label: "nav.howto" },
  { href: "/tools", label: "nav.tools" },
  { href: "/trends", label: "nav.trends" },
  { href: "/extension", label: "nav.extension" },
];

/** Header + footer for public (no-login) pages. */
export function PublicShell({ children }: { children: ReactNode }) {
  const { t } = useLanguage();
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/90 px-4 backdrop-blur-xl md:px-10">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center border border-primary/30 bg-primary/10">
            <ShieldAlert className="h-5 w-5 text-primary" />
          </span>
          <span className="text-lg font-semibold tracking-tight">ScamGuard</span>
        </Link>
        <nav className="flex items-center gap-3 text-sm md:gap-5">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="hidden text-muted-foreground hover:text-foreground sm:inline">
              {t(n.label)}
            </Link>
          ))}
          <InstallAppButton />
          <ElderToggle />
          <LanguageToggle />
          <ThemeToggle />
          <Link href="/login" className="font-medium text-muted-foreground hover:text-foreground">
            {t("nav.signin")}
          </Link>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-10 md:px-6">{children}</main>
      <footer className="border-t border-border px-4 py-6 text-center text-xs text-muted-foreground">
        {t("footer.lost")} <a href="tel:1930" className="font-semibold text-foreground">1930</a> {t("footer.report")}{" "}
        <a href="https://cybercrime.gov.in/" target="_blank" rel="noopener noreferrer" className="underline">cybercrime.gov.in</a>.
      </footer>
    </div>
  );
}
