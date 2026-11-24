"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { InstallAppButton } from "@/components/layout/install-app-button";
import { useLanguage } from "@/lib/i18n/language-context";
import type { StringKey } from "@/lib/i18n/strings";
import { cn } from "@/lib/utils";

const NAV: { href: string; label: StringKey }[] = [
  { href: "/#quick-check", label: "nav.quick" },
  { href: "/flashcards", label: "nav.howto" },
  { href: "/tools", label: "nav.tools" },
  { href: "/cross-domain", label: "nav.xdomain" },
  { href: "/trends", label: "nav.trends" },
  { href: "/extension", label: "nav.extension" },
];

/** Header + footer for public (no-login) pages. */
export function PublicShell({ children }: { children: ReactNode }) {
  const { t } = useLanguage();
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-50 flex h-[4.25rem] items-center justify-between gap-4 border-b border-border bg-background/85 px-5 backdrop-blur-xl md:px-10">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 shadow-[0_0_18px_-4px_rgba(0,229,255,0.45)]">
            <ShieldCheck className="h-4.5 w-4.5 text-primary" />
          </span>
          <span className="font-display text-lg font-bold tracking-tight">
            ScamGuard <span className="text-primary">AI</span>
          </span>
        </Link>
        <nav className="flex items-center gap-3 text-sm md:gap-5">
          {NAV.map((n) => {
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "hidden transition-colors sm:inline",
                  active ? "font-medium text-primary" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t(n.label)}
              </Link>
            );
          })}
          <InstallAppButton />
          <ThemeToggle />
          <Link href="/login" className="font-medium text-muted-foreground transition-colors hover:text-foreground">
            {t("nav.signin")}
          </Link>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 md:px-6">{children}</main>
      <footer className="border-t border-border px-4 py-6 text-center text-xs text-muted-foreground">
        {t("footer.lost")} <a href="tel:1930" className="font-semibold text-foreground">1930</a> {t("footer.report")}{" "}
        <a href="https://cybercrime.gov.in/" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">cybercrime.gov.in</a>.
      </footer>
    </div>
  );
}
