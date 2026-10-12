"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Eye, EyeOff, Moon, Sun, Trash2 } from "lucide-react";
import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";
import { useTheme } from "@/lib/theme/theme-context";
import { useLanguage } from "@/lib/i18n/language-context";
import { changePassword, deleteAccount, exportUserData, updateProfile } from "@/lib/api/users";
import { clearHistory } from "@/lib/api/messages";
import { ApiError } from "@/lib/api/client";
import { cn, formatDate } from "@/lib/utils";

const DEMO_EMAIL = "demo@scamguard.app";

const SCAN_TABS = [
  ["text", "Text message"],
  ["url", "Link"],
  ["email", "Email"],
  ["image", "Screenshot"],
  ["voice", "Voice call"],
  ["pdf", "PDF"],
  ["qr", "QR code"],
] as const;

function Section({ id, title, description, children }: { id: string; title: string; description: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="sg-card grid gap-6 border border-border p-6 md:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] md:p-8">
      <div>
        <h2 id={`${id}-title`} className="font-display text-lg font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: readonly (readonly [T, ReactNode])[]; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-xl border border-border bg-muted/40 p-1">
      {options.map(([v, node]) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          onClick={() => onChange(v)}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-sm transition-colors",
            value === v ? "bg-card text-foreground shadow-sm ring-1 ring-primary/40" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {node}
        </button>
      ))}
    </div>
  );
}

function PasswordField({ label, value, onChange, autoComplete }: { label: string; value: string; onChange: (v: string) => void; autoComplete: string }) {
  const [show, setShow] = useState(false);
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <span className="relative mt-1.5 block">
        <input
          type={show ? "text" : "password"}
          value={value}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
          className="h-11 w-full border border-border bg-background px-3 pr-11 text-sm"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground hover:text-foreground"
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
  const { lang, setLang } = useLanguage();
  const isDemo = user?.email === DEMO_EMAIL;

  const [fullName, setFullName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [defaultTab, setDefaultTab] = useState("text");

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
    { ok: newPassword.length > 0 && newPassword === confirmPassword, text: "Both new passwords match" },
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
    <div className="sg-page flex flex-col gap-6 pb-12">
      <header className="signal-aurora flex flex-wrap items-center gap-5 rounded-3xl border border-border p-6 md:p-8">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-risk-low font-display text-2xl font-bold text-primary-foreground shadow-lg">
          {initials}
        </div>
        <div className="min-w-0">
          <h1 className="font-display text-3xl font-bold">{user?.full_name || "Your account"}</h1>
          <p className="text-sm text-muted-foreground">
            {user?.email}
            {user?.created_at ? ` · member since ${formatDate(user.created_at)}` : ""}
          </p>
        </div>
      </header>

      {isDemo && (
        <p className="rounded-2xl border border-risk-medium/40 bg-risk-medium/10 p-4 text-sm">
          This is the shared demo account, so the name, password and account can&apos;t be changed. Language, theme and
          scanning choices still work.
        </p>
      )}

      <Section id="profile" title="Your name" description="Shown on your dashboard and on reports you download.">
        <form onSubmit={saveName} className="flex max-w-lg flex-col gap-3 sm:flex-row sm:items-end">
          <label className="block flex-1">
            <span className="text-sm font-medium">Full name</span>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isDemo}
              maxLength={80}
              autoComplete="name"
              className="mt-1.5 h-11 w-full border border-border bg-background px-3 text-sm disabled:opacity-60"
            />
          </label>
          <Button type="submit" isLoading={savingName} disabled={isDemo || fullName.trim() === (user?.full_name || "")}>
            Save name
          </Button>
        </form>
      </Section>

      <Section id="look" title="Language and look" description="Applies on this device straight away.">
        <div className="flex flex-col gap-5">
          <div>
            <p className="mb-2 text-sm font-medium">Language</p>
            <Segmented label="Language" value={lang} onChange={setLang} options={[["en", "English"], ["hi", "हिंदी"]] as const} />
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">Theme</p>
            <Segmented
              label="Theme"
              value={theme}
              onChange={setTheme}
              options={[["dark", <><Moon className="h-4 w-4" /> Dark</>], ["light", <><Sun className="h-4 w-4" /> Light</>]] as const}
            />
          </div>
        </div>
      </Section>

      <Section id="scanning" title="Scanning" description="Pick what the Investigate page opens on.">
        <div className="flex flex-wrap gap-2">
          {SCAN_TABS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={defaultTab === value}
              onClick={() => {
                setDefaultTab(value);
                void savePreference({ default_channel: value }, `Investigate will open on ${label}`);
              }}
              className={cn(
                "rounded-xl border px-3.5 py-2 text-sm transition-colors",
                defaultTab === value ? "border-primary/60 bg-primary/15 text-foreground" : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </Section>

      <Section id="password" title="Password" description="Use one you don't use anywhere else.">
        <form onSubmit={savePassword} className="grid max-w-lg gap-4">
          <PasswordField label="Current password" value={currentPassword} onChange={setCurrentPassword} autoComplete="current-password" />
          <PasswordField label="New password" value={newPassword} onChange={setNewPassword} autoComplete="new-password" />
          <PasswordField label="Repeat new password" value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />
          <ul className="grid grid-cols-2 gap-1.5 text-sm">
            {rules.map((r) => (
              <li key={r.text} className={r.ok ? "text-risk-low" : "text-muted-foreground"}>
                {r.ok ? "✓" : "○"} {r.text}
              </li>
            ))}
          </ul>
          <div>
            <Button type="submit" isLoading={savingPassword} disabled={isDemo || !passwordReady}>
              Change password
            </Button>
          </div>
        </form>
      </Section>

      <Section id="data" title="Your data" description="Everything ScamGuard stores about you, and how to remove it.">
        <ul className="divide-y divide-border rounded-2xl border border-border">
          <li className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="text-sm font-medium">Download my data</p>
              <p className="text-sm text-muted-foreground">Your profile and every saved scan, as a JSON file.</p>
            </div>
            <Button variant="outline" onClick={downloadData} isLoading={exporting}>
              <Download className="h-4 w-4" /> Download
            </Button>
          </li>
          <li className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="text-sm font-medium">Delete scan history</p>
              <p className="text-sm text-muted-foreground">Removes all saved scans. Your account stays.</p>
            </div>
            <Button variant="outline" onClick={() => setConfirm("clear")}>
              <Trash2 className="h-4 w-4" /> Delete history
            </Button>
          </li>
          <li className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="text-sm font-medium text-destructive">Delete account</p>
              <p className="text-sm text-muted-foreground">Permanently removes your account and all scans.</p>
            </div>
            <Button variant="destructive" onClick={() => setConfirm("delete")} disabled={isDemo}>
              Delete account
            </Button>
          </li>
        </ul>
      </Section>

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
              className="w-full max-w-md border border-border bg-card p-6"
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
                    className="mt-1.5 h-11 w-full border border-destructive/40 bg-background px-3 text-sm"
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
