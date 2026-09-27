"use client";

import { Menu, ShieldAlert } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { usePathname } from "next/navigation";

interface NavbarProps {
  onMenuClick: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const { user } = useAuth();
  const pathname = usePathname();
  const section = pathname.split("/")[1]?.replace(/-/g, " ") || "Workspace";

  return (
    <header
      className="sticky top-0 z-30 flex h-[4.5rem] items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/70 md:px-8"
    >
      <div className="flex items-center gap-3">
        <span className="hidden text-sm text-muted-foreground md:block">Workspace <span className="mx-3 text-border">/</span><span className="capitalize text-foreground">{section}</span></span>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <div className="flex items-center gap-2 md:hidden">
          <ShieldAlert className="h-5 w-5 text-primary" />
          <span className="font-semibold tracking-tight">ScamGuard</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggle />
        {user && (
          <div className="hidden items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 font-mono text-xs sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-risk-low" aria-hidden="true" />
            <span className="max-w-[180px] truncate text-foreground">{user.email}</span>
          </div>
        )}
      </div>
    </header>
  );
}
