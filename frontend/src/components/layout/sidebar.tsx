"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bot,
  BookOpen,
  FlaskConical,
  History,
  LayoutDashboard,
  LogOut,
  ScanSearch,
  Settings,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Wrench,
  X,
} from "lucide-react";
import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/auth-context";
import { useCopilot } from "@/components/copilot/copilot-provider";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const panel = useRef<HTMLElement>(null);
  useDialogFocus(isOpen, panel, onClose);
  const { user, logout } = useAuth();
  const { setOpen: openCopilot } = useCopilot();

  const prevPathRef = useRef(pathname);
  useEffect(() => {
    if (prevPathRef.current !== pathname) {
      prevPathRef.current = pathname;
      onClose();
    }
  }, [pathname, onClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  const navItems = [
    { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { href: "/analyze", label: "Scan Tool", icon: ScanSearch },
    { href: "/history", label: "History", icon: History },
    { href: "/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/trends", label: "Scam Trends", icon: TrendingUp },
    { href: "/cross-domain", label: "Cross-domain Study", icon: FlaskConical },
    { href: "/tools", label: "Safety Tools", icon: Wrench },
    { href: "/flashcards", label: "Playbooks", icon: BookOpen },
    { href: "/settings", label: "Settings", icon: Settings },
    ...(user?.role === "admin" ? [{ href: "/admin", label: "Admin Console", icon: ShieldAlert }] : []),
  ];

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={onClose}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      <aside
        ref={panel}
        aria-label="Workspace navigation"
        className={cn(
          "sg-sidebar fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card transition-transform duration-300 ease-in-out md:sticky md:top-0 md:h-screen md:translate-x-0 md:bg-background",
          isOpen ? "translate-x-0" : "-translate-x-full invisible md:visible pointer-events-none md:pointer-events-auto",
        )}
      >
        <div className="flex h-[4.5rem] items-center justify-between border-b border-border px-5">
          <Link href="/dashboard" className="group flex items-center gap-2.5" onClick={onClose}>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 text-primary shadow-[0_0_18px_-4px_rgba(0,229,255,0.45)] transition-colors duration-150 group-hover:bg-primary group-hover:text-primary-foreground">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <span className="font-display text-base font-bold leading-none tracking-tight text-foreground">
              ScamGuard <span className="text-primary">AI</span>
            </span>
          </Link>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={onClose} aria-label="Close menu">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4 pt-4">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                aria-current={isActive ? "page" : undefined}
                href={href}
                onClick={onClose}
                className={cn(
                  "relative flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm transition-colors duration-150 ease-out",
                  isActive
                    ? "font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Reference Panel 2 Bottom AI Assistant Card -> opens live Copilot */}
        <div className="space-y-2 border-t border-border p-3">
          <button
            type="button"
            onClick={() => {
              onClose();
              openCopilot(true);
            }}
            className="flex w-full items-center gap-3 rounded-xl border border-primary/30 bg-primary/10 p-3 text-left transition-colors hover:border-primary/55 hover:bg-primary/15"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/40 bg-background/70 text-primary shadow-[0_0_16px_-4px_rgba(0,229,255,0.5)]">
              <Bot className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-foreground">AI Assistant</p>
              <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">Get real-time scam safety guidance</p>
            </div>
          </button>

          <Button
            variant="ghost"
            className="w-full justify-start gap-3 text-muted-foreground hover:text-destructive"
            onClick={() => {
              onClose();
              void logout();
            }}
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </aside>
    </>
  );
}
