"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, Download, Eye, EyeOff, KeyRound, Moon, Sliders, Sun, Trash2, User } from "lucide-react";
import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";
import { useTheme } from "@/lib/theme/theme-context";
import { changePassword, deleteAccount, exportUserData, updateProfile } from "@/lib/api/users";
import { clearHistory } from "@/lib/api/messages";
import { ApiError } from "@/lib/api/client";
import { cn, formatDate } from "@/lib/utils";

const DEMO_EMAIL = "demo@scamguard.app";

const SCAN_TABS = [
  ["text", "SMS / Text"],
  ["url", "URL"],
  ["email", "Email"],
  ["image", "Screenshot"],
  ["voice", "Voice"],
  ["pdf", "PDF"],
  ["qr", "QR"],
] as const;

function PasswordField({ label, value, onChange, autoComplete }: { label: string; value: string; onChange: (v: string) => void; autoComplete: string }) {
  const [show, setShow] = useState(false);
  return (
    <label className="block">
      <span className="text-xs font-medium text-foreground">{label}</span>
      <span className="relative mt-1.5 block">
        <input
          type={show ? "text" : "password"}
          value={value}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-full border border-border bg-background px-3 pr-10 text-sm"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:text-foreground"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </span>
    </label>
  );
}

export default function SettingsPage() {
  const { toast } = useToast();
  const { user, refreshUser, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const isDemo = user?.email === DEMO_EMAIL;

  const [fullName, setFullName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [defaultTab, setDefaultTab] = useState("text");

  const [openDrawer, setOpenDrawer] = useState<"account" | "password" | "privacy" | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  const [exporting, setExporting] = useState(false);
  const [confirm, setConfirm] = useState<"clear" | "delete" | null>(null);
  const [deleteText, setDeleteText] = useState("");
  const [working, setWorking] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  const closeDialog = useCallback(() => {
    if (!working) {
      setConfirm(null);
      setDeleteText("");
    }
  }, [working]);
  useDialogFocus(confirm !== null, dialogRef, closeDialog);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name || "");
    setDefaultTab(String(user.preferences?.default_channel || "text"));
  }, [user]);

  const fail = (error: unknown, fallback: string) =>
    toast({ title: error instanceof ApiError ? error.message : fallback, variant: "error" });

  async function savePreference(patch: Record<string, unknown>, done: string) {
    try {
      await updateProfile({ preferences: { ...user?.preferences, ...patch } });
      await refreshUser();
      toast({ title: done, variant: "success" });
    } catch (e) {
      fail(e, "Couldn't save that setting. Try again.");
    }
  }

  async function saveName(e: FormEvent) {
    e.preventDefault();
    setSavingName(true);
    try {
      await updateProfile({ full_name: fullName.trim() });
      await refreshUser();
      toast({ title: "Name saved", variant: "success" });
    } catch (err) {
      fail(err, "Couldn't save your name. Try again.");
    } finally {
      setSavingName(false);
    }
  }

  const rules = [
    { ok: newPassword.length >= 8, text: "8 or more characters" },
    { ok: /\d/.test(newPassword), text: "A number" },
    { ok: /[A-Z]/.test(newPassword), text: "A capital letter" },
    { ok: newPassword.length > 0 && newPassword === confirmPassword, text: "Passwords match" },
  ];
  const passwordReady = currentPassword.length > 0 && rules.every((r) => r.ok);

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    if (!passwordReady) return;
    setSavingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast({ title: "Password changed", variant: "success" });
    } catch (err) {
      fail(err, "Couldn't change your password. Check your current password and try again.");
    } finally {
      setSavingPassword(false);
    }
  }

  async function downloadData() {
    setExporting(true);
    try {
      const data = await exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scamguard-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      toast({ title: "Your data is downloading", variant: "success" });
    } catch (err) {
      fail(err, "Couldn't prepare your data. Try again.");
    } finally {
      setExporting(false);
    }
  }

  async function runConfirmed() {
    setWorking(true);
    try {
      if (confirm === "clear") {
        await clearHistory();
        toast({ title: "Scan history deleted", variant: "success" });
        setConfirm(null);
      } else if (confirm === "delete") {
        await deleteAccount();
        await logout();
        toast({ title: "Account deleted", variant: "success" });
      }
    } catch (err) {
      fail(err, "That didn't work. Try again.");
    } finally {
      setWorking(false);
    }
  }

  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  return (
    <div className="sg-page mx-auto flex max-w-4xl flex-col gap-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-primary/40 bg-primary/15 font-display text-lg font-bold text-primary shadow-[0_0_20px_-6px_rgba(0,229,255,0.45)]">
            {initials}
          </div>
          <div>
            <p className="console-kicker mb-0.5">Workspace Preferences</p>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Settings</h1>
            <p className="font-mono text-xs text-muted-foreground">
              {user?.email}
              {user?.created_at ? ` · member since ${formatDate(user.created_at)}` : ""}
            </p>
          </div>
        </div>
      </div>

      {isDemo && (
        <p className="rounded-xl border border-caution/30 bg-caution/10 px-4 py-3 text-xs leading-relaxed text-foreground/90">
          This is the shared demo account, so profile name, password, and account deletion are disabled. Theme and default scan preferences still apply.
        </p>
      )}

      {/* Panel 13 Unified Settings Container */}
      <div className="console-panel divide-y divide-border overflow-hidden">
        {/* Account row */}
        <div>
          <button
            type="button"
            aria-expanded={openDrawer === "account"}
            onClick={() => setOpenDrawer(openDrawer === "account" ? null : "account")}
            className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/20 sm:px-6"
          >
            <div className="flex items-center gap-3.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
                <User className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <p className="font-medium text-foreground">Account</p>
                <p className="text-xs text-muted-foreground">
                  Display name: {user?.full_name || "Not set"} · Manage profile identity
                </p>
              </div>
            </div>
            <ChevronRight className={cn("h-4 w-4 text-muted-foreground transition-transform", openDrawer === "account" && "rotate-90 text-primary")} />
          </button>

          {openDrawer === "account" && (
            <form onSubmit={saveName} className="flex flex-col gap-3 border-t border-border/50 bg-background/35 px-5 py-4 sm:flex-row sm:items-end sm:px-6">
              <label className="block flex-1">
                <span className="text-xs font-medium text-muted-foreground">Full name</span>
                <input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={isDemo}
                  maxLength={80}
                  autoComplete="name"
                  className="mt-1.5 h-10 w-full border border-border bg-background px-3 text-sm disabled:opacity-60"
                />
              </label>
              <Button type="submit" size="sm" isLoading={savingName} disabled={isDemo || fullName.trim() === (user?.full_name || "")}>
                Save name
              </Button>
            </form>
          )}
        </div>

        {/* Theme row */}
        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
              {theme === "dark" ? <Moon className="h-4 w-4" aria-hidden="true" /> : <Sun className="h-4 w-4" aria-hidden="true" />}
            </span>
            <div>
              <p className="font-medium text-foreground">Theme</p>
              <p className="text-xs text-muted-foreground">Switch between obsidian dark and daylight interfaces</p>
            </div>
          </div>
          <div role="radiogroup" aria-label="Theme" className="inline-flex rounded-lg border border-border bg-muted/40 p-1">
            {(
              [
                ["dark", "Dark", Moon],
                ["light", "Light", Sun],
              ] as const
            ).map(([val, label, Icon]) => (
              <button
                key={val}
                type="button"
                role="radio"
                aria-checked={theme === val}
                onClick={() => setTheme(val)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors",
                  theme === val ? "bg-card text-primary shadow-sm ring-1 ring-primary/35" : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Default Scan Channel row */}
        <div className="flex flex-col justify-between gap-3 px-5 py-4 sm:px-6 lg:flex-row lg:items-center">
          <div className="flex items-center gap-3.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
              <Sliders className="h-4 w-4" aria-hidden="true" />
            </span>
            <div>
              <p className="font-medium text-foreground">Default Scan Channel</p>
              <p className="text-xs text-muted-foreground">Choose the tab Scan Tool opens on</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {SCAN_TABS.map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={defaultTab === value}
                onClick={() => {
                  setDefaultTab(value);
                  void savePreference({ default_channel: value }, `Scan Tool will open on ${label}`);
                }}
                className={cn(
                  "rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors",
                  defaultTab === value
                    ? "border-primary/50 bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Password row */}
        <div>
          <button
            type="button"
            aria-expanded={openDrawer === "password"}
            onClick={() => setOpenDrawer(openDrawer === "password" ? null : "password")}
            className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/20 sm:px-6"
          >
            <div className="flex items-center gap-3.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
                <KeyRound className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <p className="font-medium text-foreground">Password</p>
                <p className="text-xs text-muted-foreground">Update your workspace authentication password</p>
              </div>
            </div>
            <ChevronRight className={cn("h-4 w-4 text-muted-foreground transition-transform", openDrawer === "password" && "rotate-90 text-primary")} />
          </button>

          {openDrawer === "password" && (
            <form onSubmit={savePassword} className="grid max-w-xl gap-3.5 border-t border-border/50 bg-background/35 px-5 py-4 sm:px-6">
              <PasswordField label="Current password" value={currentPassword} onChange={setCurrentPassword} autoComplete="current-password" />
              <div className="grid gap-3.5 sm:grid-cols-2">
                <PasswordField label="New password" value={newPassword} onChange={setNewPassword} autoComplete="new-password" />
                <PasswordField label="Repeat new password" value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />
              </div>
              <ul className="grid grid-cols-2 gap-1 text-xs">
                {rules.map((r) => (
                  <li key={r.text} className={r.ok ? "text-safe" : "text-muted-foreground"}>
                    {r.ok ? "✓" : "○"} {r.text}
                  </li>
                ))}
              </ul>
              <div>
                <Button type="submit" size="sm" isLoading={savingPassword} disabled={isDemo || !passwordReady}>
                  Change password
                </Button>
              </div>
            </form>
          )}
        </div>

        {/* Privacy & Data row */}
        <div>
          <button
            type="button"
            aria-expanded={openDrawer === "privacy"}
            onClick={() => setOpenDrawer(openDrawer === "privacy" ? null : "privacy")}
            className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/20 sm:px-6"
          >
            <div className="flex items-center gap-3.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
                <Download className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <p className="font-medium text-foreground">Privacy &amp; Data</p>
                <p className="text-xs text-muted-foreground">Export your workspace JSON, wipe scan history, or delete account</p>
              </div>
            </div>
            <ChevronRight className={cn("h-4 w-4 text-muted-foreground transition-transform", openDrawer === "privacy" && "rotate-90 text-primary")} />
          </button>

          {openDrawer === "privacy" && (
            <div className="flex flex-wrap items-center gap-3 border-t border-border/50 bg-background/35 px-5 py-4 sm:px-6">
              <Button variant="outline" size="sm" onClick={downloadData} isLoading={exporting}>
                <Download className="h-3.5 w-3.5" aria-hidden="true" /> Export my data
              </Button>
              <Button variant="outline" size="sm" onClick={() => setConfirm("clear")}>
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" /> Delete scan history
              </Button>
              <Button variant="destructive" size="sm" onClick={() => setConfirm("delete")} disabled={isDemo}>
                Delete account
              </Button>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {confirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={closeDialog}>
            <motion.div
              ref={dialogRef}
              role="dialog"
              aria-modal="true"
              aria-label={confirm === "clear" ? "Delete scan history" : "Delete account"}
              tabIndex={-1}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              onClick={(e) => e.stopPropagation()}
              className="console-panel w-full max-w-md bg-card p-6"
            >
              <h3 className="font-display text-xl font-semibold">
                {confirm === "clear" ? "Delete all saved scans?" : "Delete your account?"}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {confirm === "clear"
                  ? "Every saved scan will be removed. This can't be undone."
                  : "Your account and every saved scan will be removed. This can't be undone."}
              </p>
              {confirm === "delete" && (
                <label className="mt-4 block text-sm">
                  Type <strong>DELETE</strong> to confirm
                  <input
                    value={deleteText}
                    onChange={(e) => setDeleteText(e.target.value)}
                    className="mt-1.5 h-10 w-full border border-destructive/40 bg-background px-3 text-sm"
                  />
                </label>
              )}
              <div className="mt-6 flex justify-end gap-3">
                <Button variant="outline" onClick={closeDialog} disabled={working}>
                  Keep {confirm === "clear" ? "history" : "account"}
                </Button>
                <Button
                  variant="destructive"
                  onClick={runConfirmed}
                  isLoading={working}
                  disabled={confirm === "delete" && deleteText !== "DELETE"}
                >
                  {confirm === "clear" ? "Delete history" : "Delete account"}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
