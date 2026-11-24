"use client";

import { useState } from "react";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { crossDomainClassify, type CdClassification, type CdClassifier } from "@/lib/api/public";
import { cn } from "@/lib/utils";

/** The Indian examples come from the held-out Indian test set (seed 42). */
const EXAMPLES: { label: string; text: string }[] = [
  {
    label: "Indian scam SMS",
    text: "Hi 901969XXXX, Rs.56,6OO/- bonus is credited t0 your wallet n0 XX32 0n 28 Aug. Directly move to your bank a/c n0w oi1.in/2uabg2!8cpr814",
  },
  {
    label: "Indian telecom offer",
    text: "Free 2GB data for data lovers like you! Now get 2GB data on Airtel Thanks app, download now i.airtel.in/2gb_rc2",
  },
  {
    label: "Indian shopping offer",
    text: "Lenskart online MEGA SALE: Buy1Get1 FREE + upto 40% off on eye & sunglasses! Fresh stocks added. TnC shop lskt.me/megasale",
  },
  {
    label: "Normal Indian message",
    text: "Hi team, we are having a power cut due to heavy rain that started 5 mins ago",
  },
  {
    label: "UK spam",
    text: "WINNER!! As a valued network customer you have been selected to receive a £900 prize reward! To claim call 09061701461. Claim code KL341. Valid 12 hours only.",
  },
];

const CLASSIFIERS: { id: CdClassifier; label: string }[] = [
  { id: "logistic_regression", label: "Logistic Regression" },
  { id: "naive_bayes", label: "Naive Bayes" },
];

function ResultCard({ title, subtitle, result }: { title: string; subtitle: string; result: CdClassification }) {
  const spam = result.label === "spam";
  const p = result.spam_probability;
  const top = result.top_features.slice(0, 6);
  const max = Math.max(0.0001, ...top.map((f) => Math.abs(f.contribution)));
  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        spam ? "border-destructive/40 bg-destructive/5" : "border-primary/35 bg-primary/5",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <span
          className={cn(
            "rounded-md px-2.5 py-0.5 font-mono text-xs font-bold",
            spam ? "bg-destructive/15 text-destructive" : "bg-primary/15 text-primary",
          )}
        >
          {spam ? "SPAM" : "HAM"}
        </span>
      </div>

      <div className="mt-4 flex items-baseline justify-between gap-3">
        <span className="text-xs text-muted-foreground">Spam probability</span>
        <span className="font-mono text-xl font-bold tabular-nums text-foreground">{p.toFixed(3)}</span>
      </div>

      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden="true">
        <div
          className={cn("h-full rounded-full transition-all duration-300", spam ? "bg-destructive" : "bg-primary")}
          style={{ width: `${Math.max(3, p * 100)}%` }}
        />
      </div>

      <p className="mt-4 text-xs font-medium text-foreground">Top contributing tokens</p>
      {top.length === 0 ? (
        <p className="mt-1.5 text-xs text-muted-foreground">None of these tokens exist in this model&apos;s vocabulary.</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {top.map((f) => (
            <li key={f.feature} className="grid grid-cols-[6.5rem_1fr_3.2rem] items-center gap-2 text-xs">
              <span className="truncate font-mono text-foreground/90" title={f.feature}>
                {f.feature}
              </span>
              <span className="h-1.5 overflow-hidden rounded-full bg-muted">
                <span
                  className={cn("block h-full rounded-full", f.contribution > 0 ? "bg-destructive" : "bg-primary")}
                  style={{ width: `${(Math.abs(f.contribution) / max) * 100}%` }}
                />
              </span>
              <span className="text-right font-mono tabular-nums text-muted-foreground">
                {f.contribution > 0 ? "+" : ""}
                {f.contribution.toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <dl className="mt-4 flex flex-wrap gap-x-4 gap-y-1 border-t border-border/60 pt-3 font-mono text-[11px] text-muted-foreground">
        <div>
          <dt className="inline">Model </dt>
          <dd className="inline text-foreground">{result.model.id}</dd>
        </div>
        {result.model.train_messages != null && (
          <div>
            <dt className="inline">Train </dt>
            <dd className="inline">{result.model.train_messages.toLocaleString("en-IN")}</dd>
          </div>
        )}
        {result.model.target_test_f1 != null && (
          <div>
            <dt className="inline">Indian F1 </dt>
            <dd className="inline font-semibold text-primary">{result.model.target_test_f1.toFixed(3)}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

/** One message through the UK-only model and the adapted model, side by side. */
export function ComparePanel() {
  const [text, setText] = useState("");
  const [classifier, setClassifier] = useState<CdClassifier>("logistic_regression");
  const [pair, setPair] = useState<{ base: CdClassification; adapted: CdClassification } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(message = text, clf = classifier) {
    if (!message.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const [base, adapted] = await Promise.all([
        crossDomainClassify(message, clf, "baseline"),
        crossDomainClassify(message, clf, "adapted40"),
      ]);
      setPair({ base, adapted });
    } catch {
      setError("Could not classify the message. Try again in a few seconds.");
    } finally {
      setBusy(false);
    }
  }

  const changed = pair && pair.base.label !== pair.adapted.label;

  return (
    <section className="scanner-panel mt-6 p-6" aria-labelledby="cd-compare">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="console-kicker mb-1">Interactive Inference</p>
          <h2 id="cd-compare" className="text-xl font-semibold text-foreground">
            Baseline vs Adapted Workbench
          </h2>
        </div>
        <div role="radiogroup" aria-label="Classifier" className="inline-flex rounded-lg border border-border bg-muted/40 p-1">
          {CLASSIFIERS.map((c) => (
            <button
              key={c.id}
              type="button"
              role="radio"
              aria-checked={classifier === c.id}
              onClick={() => {
                setClassifier(c.id);
                if (text.trim()) void run(text, c.id);
              }}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                classifier === c.id ? "bg-card text-primary shadow-sm ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Examples:</span>
        {EXAMPLES.map((e) => (
          <button
            key={e.label}
            type="button"
            onClick={() => {
              setText(e.text);
              void run(e.text);
            }}
            className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/45 hover:text-foreground"
          >
            <Sparkles className="h-3 w-3 text-primary" aria-hidden="true" />
            {e.label}
          </button>
        ))}
      </div>

      <textarea
        id="cd-text"
        aria-label="Message to classify"
        value={text}
        maxLength={2000}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder="Paste an SMS to compare UK-baseline vs Indian-adapted predictions..."
        className="mt-4 w-full border border-border bg-background/85 p-3.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none"
      />

      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="font-mono text-[11px] text-muted-foreground">{text.length}/2000</span>
        <Button onClick={() => void run()} disabled={busy || !text.trim()}>
          {busy ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              Comparing…
            </>
          ) : (
            "Compare Models"
          )}
        </Button>
      </div>

      {error && <p role="alert" className="mt-3 text-sm text-destructive">{error}</p>}

      {pair && (
        <>
          <div
            className={cn(
              "mt-5 rounded-xl border px-4 py-3 text-sm",
              changed ? "border-primary/40 bg-primary/10" : "border-border bg-muted/35",
            )}
            role="status"
          >
            {changed ? (
              <>
                <strong className="text-primary">Decision shifted:</strong> Baseline{" "}
                <span className="font-mono font-semibold">{pair.base.label.toUpperCase()}</span> (
                {pair.base.spam_probability.toFixed(3)}) → Adapted{" "}
                <span className="font-mono font-semibold">{pair.adapted.label.toUpperCase()}</span> (
                {pair.adapted.spam_probability.toFixed(3)})
              </>
            ) : (
              <>
                <strong>Both models agree: {pair.base.label.toUpperCase()}</strong>{" "}
                <span className="font-mono text-xs text-muted-foreground">
                  ({pair.base.spam_probability.toFixed(3)} → {pair.adapted.spam_probability.toFixed(3)})
                </span>
              </>
            )}
          </div>
          <div className="mt-4 grid items-stretch gap-4 lg:grid-cols-[1fr_auto_1fr]">
            <ResultCard title="Baseline" subtitle="Trained on UK SMS (UCI)" result={pair.base} />
            <div className="hidden items-center justify-center lg:flex" aria-hidden="true">
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </div>
            <ResultCard title="Adapted" subtitle="UK SMS + 40% Indian labels" result={pair.adapted} />
          </div>
        </>
      )}
    </section>
  );
}
