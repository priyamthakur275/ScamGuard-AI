"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { HeartHandshake, ShieldAlert, UserPlus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth/auth-context";
import { ApiError } from "@/lib/api/client";
import {
  acceptLink, declineLink, inviteGuardian, listFamilyAlerts, listGuardians, listProtecting, removeLink,
  type FamilyAlert, type FamilyLink,
} from "@/lib/api/family";
import { cn, formatDate, inputTypeLabel, scamCategoryLabel } from "@/lib/utils";

const STATUS: Record<FamilyLink["status"], string> = { pending: "Waiting for them to accept", active: "Watching out for you", declined: "Declined" };

export default function FamilyPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const isDemo = user?.email === "demo@scamguard.app";
  const [guardians, setGuardians] = useState<FamilyLink[] | null>(null);
  const [protecting, setProtecting] = useState<FamilyLink[] | null>(null);
  const [alerts, setAlerts] = useState<FamilyAlert[] | null>(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [g, p, a] = await Promise.all([listGuardians(), listProtecting(), listFamilyAlerts()]);
      setGuardians(g);
      setProtecting(p);
      setAlerts(a);
    } catch {
      toast({ title: "Couldn't load your family settings. Refresh to try again.", variant: "error" });
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(key: string, fn: () => Promise<unknown>, done: string) {
    setBusy(key);
    try {
      await fn();
      toast({ title: done, variant: "success" });
      await load();
    } catch (e) {
      toast({ title: e instanceof ApiError ? e.message : "That didn't work. Try again.", variant: "error" });
    } finally {
      setBusy(null);
    }
  }

  async function invite(e: FormEvent) {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    await act("invite", () => inviteGuardian(value), `Invitation sent to ${value}`);
    setEmail("");
  }

  const pending = (protecting ?? []).filter((l) => l.status === "pending");
  const active = (protecting ?? []).filter((l) => l.status === "active");

  return (
    <div className="sg-page flex flex-col gap-6 pb-12">
      <header className="signal-aurora rounded-3xl border border-border p-6 md:p-8">
        <div className="flex items-center gap-3">
          <HeartHandshake className="h-7 w-7 text-primary" />
          <h1 className="font-display text-3xl font-bold">Family guardian</h1>
        </div>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Most scam victims in India are parents and grandparents. Link a family member and, whenever one of you checks a
          high-risk scam, the other sees it here and can call before any money is sent.
        </p>
      </header>

      {pending.length > 0 && (
        <section className="sg-card border border-primary/40 p-6">
          <h2 className="font-display text-lg font-semibold">Requests for you</h2>
          <ul className="mt-3 divide-y divide-border">
            {pending.map((l) => (
              <li key={l.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <p className="text-sm">
                  <strong>{l.name || l.email}</strong> wants you to watch out for scams sent to them.
                  <span className="block text-muted-foreground">You&apos;ll see only their high-risk scans, from today.</span>
                </p>
                <div className="flex gap-2">
                  <Button size="sm" isLoading={busy === `a-${l.id}`} onClick={() => act(`a-${l.id}`, () => acceptLink(l.id), `You're now watching out for ${l.name || l.email}`)}>
                    Accept
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => act(`d-${l.id}`, () => declineLink(l.id), "Request declined")}>
                    Decline
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="sg-card border border-border p-6">
        <h2 className="font-display text-lg font-semibold">Alerts from people you protect</h2>
        {alerts === null ? (
          <div className="mt-4 space-y-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : active.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            You aren&apos;t watching out for anyone yet. When a family member adds your email below on their account, their
            request will appear here.
          </p>
        ) : alerts.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            No high-risk scams in the last 30 days for {active.map((l) => l.name || l.email).join(", ")}.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {alerts.map((a) => (
              <li key={a.id} className="rounded-2xl border border-destructive/40 bg-destructive/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="flex items-center gap-2 font-medium">
                    <ShieldAlert className="h-4 w-4 text-destructive" />
                    {a.person} checked a likely scam
                  </p>
                  <span className="text-sm text-muted-foreground">{a.created_at ? formatDate(a.created_at) : ""}</span>
                </div>
                <p className="mt-2 text-sm">“{a.preview}”</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {Math.round(a.threat_score * 100)}% scam likelihood
                  {a.scam_category ? ` · ${scamCategoryLabel(a.scam_category)}` : ""} · {inputTypeLabel(a.input_type)}
                </p>
                <p className="mt-2 text-sm font-medium">Call them now and make sure they haven&apos;t paid or shared an OTP.</p>
              </li>
            ))}
          </ul>
        )}
        {active.length > 0 && (
          <ul className="mt-5 flex flex-wrap gap-2">
            {active.map((l) => (
              <li key={l.id} className="flex items-center gap-2 rounded-full border border-border px-3 py-1 text-sm">
                Protecting {l.name || l.email}
                <button aria-label={`Stop protecting ${l.name || l.email}`} onClick={() => act(`r-${l.id}`, () => removeLink(l.id), "Stopped")} className="text-muted-foreground hover:text-destructive">
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="sg-card border border-border p-6">
        <h2 className="font-display text-lg font-semibold">People watching out for you</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Add a son, daughter or anyone you trust. They need a ScamGuard account with this email. They&apos;ll see only your
          high-risk scans, never your other messages.
        </p>
        <form onSubmit={invite} className="mt-4 flex max-w-lg flex-col gap-2 sm:flex-row">
          <input
            type="email"
            aria-label="Family member's email"
            placeholder="family.member@gmail.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isDemo}
            className="h-11 flex-1 border border-border bg-background px-3 text-sm"
          />
          <Button type="submit" isLoading={busy === "invite"} disabled={isDemo || !email.trim()}>
            <UserPlus className="h-4 w-4" /> Add family member
          </Button>
        </form>
        {isDemo && <p className="mt-2 text-sm text-risk-medium">The shared demo account can&apos;t add family members. Create your own account to try this.</p>}
        {guardians && guardians.length > 0 && (
          <ul className="mt-4 divide-y divide-border rounded-2xl border border-border">
            {guardians.map((g) => (
              <li key={g.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="text-sm font-medium">{g.name || g.email}</p>
                  <p className={cn("text-sm", g.status === "active" ? "text-risk-low" : "text-muted-foreground")}>{STATUS[g.status]}</p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => act(`g-${g.id}`, () => removeLink(g.id), "Removed")}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
