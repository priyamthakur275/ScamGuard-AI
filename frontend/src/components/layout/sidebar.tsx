"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FolderKanban,
  History,
  LayoutDashboard,
  LogOut,
  ScanSearch,
  Settings,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/auth-context";
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

  // Only close sidebar when actually navigating to a DIFFERENT route
  const prevPathRef = useRef(pathname);
  useEffect(() => {
    if (prevPathRef.current !== pathname) {
      prevPathRef.current = pathname;
      onClose();
    }
  }, [pathname, onClose]);

  // Handle Escape key and body scroll lock when mobile sidebar is open
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
    { href: "/analyze", label: "Investigate", icon: ScanSearch },
    { href: "/demo", label: "Demo Mode", icon: Sparkles },
    { href: "/history", label: "History", icon: History },
    { href: "/cases", label: "Cases", icon: FolderKanban },
    { href: "/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/settings", label: "Settings", icon: Settings },
    ...(user?.role === "admin" ? [{ href: "/admin", label: "Admin Console", icon: ShieldAlert }] : []),
  ];

  return (
    <>
      {/* Mobile Backdrop */}
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

      {/* Sidebar Navigation */}
      <aside ref={panel} aria-label="Workspace navigation"
        className={cn(
          "sg-sidebar fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-border bg-card transition-transform duration-300 ease-in-out md:sticky md:top-0 md:h-screen md:translate-x-0 md:bg-background",
          isOpen ? "translate-x-0" : "-translate-x-full invisible md:visible pointer-events-none md:pointer-events-auto"
        )}
      >
        <div className="flex h-[4.5rem] items-center justify-between border-b border-border px-6">
          <Link href="/dashboard" className="group flex items-center gap-2.5" onClick={onClose}>
            <div className="flex h-9 w-9 items-center justify-center rounded-sm border border-primary/30 bg-primary/10 text-primary transition-colors duration-150 group-hover:bg-primary group-hover:text-primary-foreground">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold leading-none tracking-tight text-foreground">ScamGuard</span>
              <span className="mt-1 font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-primary">Threat Intel</span>
            </div>
          </Link>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={onClose} aria-label="Close menu">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="px-6 pb-2 pt-7 console-kicker">Workspace</div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-6">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                aria-current={isActive ? "page" : undefined}
                href={href}
                onClick={onClose}
                className={cn(
                  "relative flex items-center gap-3 rounded-sm px-3.5 py-2.5 text-sm transition-colors duration-150 ease-out",
                  isActive
                    ? "bg-primary/10 font-medium text-primary shadow-[inset_0_0_0_1px_rgba(34,211,238,0.08)]"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {isActive && <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-primary" />}
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-3">
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
