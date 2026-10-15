"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, FileWarning, Info, Loader2, QrCode, ShieldAlert, Upload, Wallet } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { checkFile, checkQr, getPayReasons, payCheck, type QrResult, type ToolFlag, type ToolResult } from "@/lib/api/tools";
import { cn, scamCategoryLabel } from "@/lib/utils";

type Tab = "qr" | "pay" | "file";
const TABS: { id: Tab; label: string; icon: typeof QrCode; blurb: string }[] = [
  { id: "qr", label: "QR code check", icon: QrCode, blurb: "See who a QR code really pays, how much, or where its link goes, before you scan it in your UPI app." },
  { id: "pay", label: "Before you pay", icon: Wallet, blurb: "Someone asked you to pay? Check the UPI ID and the reason against known payment scams." },
  { id: "file", label: "File check", icon: FileWarning, blurb: "Got an attachment on WhatsApp or email? Find out what it really is before you open or install it." },
];

const FLAG_STYLE: Record<ToolFlag["level"], { icon: typeof Info; cls: string }> = {
  danger: { icon: ShieldAlert, cls: "border-destructive/40 bg-destructive/10 text-destructive" },
  warning: { icon: AlertTriangle, cls: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400" },
  info: { icon: Info, cls: "border-border bg-muted/50 text-foreground" },
  ok: { icon: CheckCircle2, cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400" },
};
const RISK_STYLE = {
  high: "border-destructive bg-destructive text-destructive-foreground",
  medium: "border-amber-500 bg-amber-500 text-black",
  low: "border-emerald-600 bg-emerald-600 text-white",
};
const FACT_LABEL: Record<string, string> = {
  upi_id: "UPI ID", payee_name: "Payee name", amount: "Amount (₹)", note: "Note", file_name: "File", size_bytes: "Size",
  detected_type: "Real file type", sha256: "SHA-256",
};

function ResultView({ result }: { result: ToolResult }) {
  const facts = Object.entries(result.facts).filter(([k]) => k !== "virustotal_url");
  return (
    <div className="space-y-4" role="status">
      <div className={cn("rounded-2xl border px-5 py-4", RISK_STYLE[result.risk])}>
        <p className="text-xs font-semibold uppercase tracking-wider opacity-80">{result.risk} risk</p>
        <p className="text-lg font-semibold">{result.summary}</p>
      </div>
      <ul className="space-y-2">
        {result.flags.map((f) => {
          const { icon: Icon, cls } = FLAG_STYLE[f.level];
          return (
            <li key={f.title} className={cn("flex gap-3 rounded-xl border p-3", cls)}>
              <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
              <div>
                <p className="font-medium">{f.title}</p>
                <p className="text-sm text-foreground/80">{f.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>
      {facts.length > 0 && (
        <dl className="grid gap-x-4 gap-y-1 rounded-xl border border-border p-3 text-sm sm:grid-cols-[auto,1fr]">
          {facts.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted-foreground">{FACT_LABEL[k] ?? k}</dt>
              <dd className="break-all font-mono text-xs sm:text-sm">{k === "size_bytes" ? `${(Number(v) / 1024).toFixed(1)} KB` : String(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      {typeof result.facts.virustotal_url === "string" && (
        <a href={result.facts.virustotal_url} target="_blank" rel="noopener noreferrer" className="inline-block text-sm text-primary underline">
          Look up this file&apos;s fingerprint on VirusTotal (the file itself is not uploaded there)
        </a>
      )}
    </div>
  );
}

function FilePicker({ accept, label, hint, busy, onFile }: { accept?: string; label: string; hint: string; busy: boolean; onFile: (f: File) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
      className={cn("flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed p-8 text-center transition-colors", drag ? "border-primary bg-primary/5" : "border-border")}
    >
      {busy ? <Loader2 className="h-8 w-8 animate-spin text-primary" /> : <Upload className="h-8 w-8 text-muted-foreground" />}
      <button type="button" disabled={busy} onClick={() => ref.current?.click()}
        className="rounded-xl bg-primary px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-60">
        {busy ? "Checking…" : label}
      </button>
      <p className="max-w-sm text-xs text-muted-foreground">{hint}</p>
      <input ref={ref} type="file" accept={accept} className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </div>
  );
}

function useRun<T>() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);
  const run = async (fn: () => Promise<T>) => {
    setBusy(true); setError(null); setData(null);
    try { setData(await fn()); } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong. Please try again."); } finally { setBusy(false); }
  };
  return { busy, error, data, run };
}

function ErrorNote({ error }: { error: string | null }) {
  return error ? <p role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">{error}</p> : null;
}

function QrTool() {
  const { busy, error, data, run } = useRun<QrResult>();
  return (
    <div className="space-y-5">
      <FilePicker accept="image/*" label="Upload or photograph the QR code" busy={busy} onFile={(f) => run(() => checkQr(f))}
        hint="A screenshot or a clear photo works. Nothing is paid or saved; we only read what the code contains." />
      <ErrorNote error={error} />
      {data?.kind === "upi" && <ResultView result={data} />}
      {data && data.kind !== "upi" && (
        <div className="space-y-3 rounded-2xl border border-border p-4">
          <p className="text-sm text-muted-foreground">This QR code is not a UPI payment. It contains:</p>
          <p className="break-all rounded-lg bg-muted p-3 font-mono text-sm">{data.content}</p>
          {data.analysis && (
            <div className={cn("rounded-xl border px-4 py-3", data.analysis.verdict === "legitimate" ? RISK_STYLE.low : RISK_STYLE.high)}>
              <p className="font-semibold">
                {data.analysis.verdict === "legitimate" ? "No scam signs found" : "Likely scam"} · {Math.round(data.analysis.threat_score * 100)}% risk
              </p>
              {data.analysis.scam_category && <p className="text-sm opacity-90">{scamCategoryLabel(data.analysis.scam_category)}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PayTool() {
  const [reasons, setReasons] = useState<{ id: string; label: string }[]>([]);
  const [form, setForm] = useState({ upi_id: "", payee_name: "", expected_name: "", amount: "", reason: "" });
  const { busy, error, data, run } = useRun<ToolResult>();
  useEffect(() => { getPayReasons().then(setReasons).catch(() => setReasons([])); }, []);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const submit = (e: FormEvent) => { e.preventDefault(); void run(() => payCheck({ ...form, reason: form.reason || "other" })); };
  const field = "w-full rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary";
  return (
    <div className="space-y-5">
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1 text-sm sm:col-span-2">
          <span className="font-medium">Why are you being asked to pay?</span>
          <select required value={form.reason} onChange={set("reason")} className={field}>
            <option value="" disabled>Choose the reason…</option>
            {reasons.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-sm"><span className="font-medium">UPI ID to pay</span>
          <input value={form.upi_id} onChange={set("upi_id")} placeholder="name@bank" maxLength={256} className={field} autoComplete="off" /></label>
        <label className="space-y-1 text-sm"><span className="font-medium">Amount (₹)</span>
          <input value={form.amount} onChange={set("amount")} inputMode="decimal" placeholder="Optional" maxLength={20} className={field} /></label>
        <label className="space-y-1 text-sm"><span className="font-medium">Name your UPI app shows</span>
          <input value={form.payee_name} onChange={set("payee_name")} placeholder="Optional" maxLength={120} className={field} /></label>
        <label className="space-y-1 text-sm"><span className="font-medium">Who you think you are paying</span>
          <input value={form.expected_name} onChange={set("expected_name")} placeholder="Optional, e.g. Ramesh Kirana" maxLength={120} className={field} /></label>
        <button type="submit" disabled={busy} className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-60 sm:col-span-2">
          {busy && <Loader2 className="h-4 w-4 animate-spin" />} Check before paying
        </button>
      </form>
      <p className="text-xs text-muted-foreground">Never type your UPI PIN anywhere except inside your own UPI app. ScamGuard never asks for it.</p>
      <ErrorNote error={error} />
      {data && <ResultView result={data} />}
    </div>
  );
}

function FileTool() {
  const { busy, error, data, run } = useRun<ToolResult>();
  return (
    <div className="space-y-5">
      <FilePicker label="Choose the file to check" busy={busy} onFile={(f) => run(() => checkFile(f))}
        hint="Up to 10 MB. The file is inspected in memory and never stored, and it is never opened or run." />
      <ErrorNote error={error} />
      {data && <ResultView result={data} />}
    </div>
  );
}

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("qr");
  const active = TABS.find((t) => t.id === tab)!;
  const panels: Record<Tab, ReactNode> = { qr: <QrTool />, pay: <PayTool />, file: <FileTool /> };
  return (
    <PublicShell>
      <div className="mx-auto max-w-3xl px-4 py-10 sm:py-14">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Safety tools</h1>
        <p className="mt-2 text-muted-foreground">Check a QR code, a payment request or a file before it costs you money. No sign-up, nothing stored.</p>
        <div role="tablist" aria-label="Safety tools" className="mt-8 grid grid-cols-3 gap-2">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} role="tab" type="button" aria-selected={tab === id} aria-controls={`panel-${id}`} id={`tab-${id}`} onClick={() => setTab(id)}
              className={cn("flex flex-col items-center gap-1.5 rounded-2xl border px-2 py-3 text-xs font-medium sm:flex-row sm:justify-center sm:text-sm",
                tab === id ? "border-primary bg-primary/10 text-primary" : "border-border hover:border-primary/50")}>
              <Icon className="h-5 w-5" aria-hidden /> {label}
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="mt-6 space-y-5">
          <p className="text-sm text-muted-foreground">{active.blurb}</p>
          {panels[tab]}
        </div>
      </div>
    </PublicShell>
  );
}
