"use client";

import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
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
    <div className={cn("rounded-xl border p-4", spam ? "border-destructive/50 bg-destructive/5" : "border-primary/40 bg-primary/5")}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="text-xs text-muted-foreground">{subtitle}</p>
      <div className="mt-3 flex items-baseline gap-3">
        <span className={cn("text-3xl font-bold", spam ? "text-destructive" : "text-primary")}>{spam ? "SPAM" : "HAM"}</span>
        <span className="text-sm text-muted-foreground">
          probability of spam <span className="font-semibold tabular-nums text-foreground">{p.toFixed(3)}</span>
        </span>
      </div>
      <div className="mt-2 h-2 w-full rounded bg-muted" aria-hidden>
        <div className={cn("h-2 rounded", spam ? "bg-destructive" : "bg-primary")} style={{ width: `${Math.max(2, p * 100)}%` }} />
      </div>
      <p className="mt-1 text-[11px] text-muted-foreground">Spam if the probability is 0.5 or more.</p>
      <p className="mt-4 text-xs font-medium">Top words</p>
      {top.length === 0 ? (
        <p className="mt-1 text-xs text-muted-foreground">None of these words are in this model&apos;s vocabulary.</p>
      ) : (
        <ul className="mt-1 space-y-1">
          {top.map((f) => (
            <li key={f.feature} className="grid grid-cols-[7rem_1fr_3.2rem] items-center gap-2 text-xs">
              <span className="truncate font-mono" title={f.feature}>{f.feature}</span>
              <span className="h-1.5 bg-muted">
                <span className={cn("block h-1.5", f.contribution > 0 ? "bg-destructive" : "bg-primary")} style={{ width: `${(Math.abs(f.contribution) / max) * 100}%` }} />
              </span>
              <span className="text-right tabular-nums">{f.contribution > 0 ? "+" : ""}{f.contribution.toFixed(2)}</span>
            </li>
          ))}
        </ul>
      )}
      <dl className="mt-3 space-y-0.5 text-[11px] text-muted-foreground">
        <div><dt className="inline">Model: </dt><dd className="inline font-mono">{result.model.id}</dd></div>
        {result.model.train_messages != null && (
          <div><dt className="inline">Trained on: </dt><dd className="inline">{result.model.train_messages.toLocaleString("en-IN")} messages</dd></div>
        )}
        {result.model.target_test_f1 != null && (
          <div><dt className="inline">Spam F1 on the Indian test set: </dt><dd className="inline font-semibold">{result.model.target_test_f1.toFixed(3)}</dd></div>
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
    <section className="mt-6 rounded-xl border border-primary/40 p-5" aria-labelledby="cd-compare">
      <h2 id="cd-compare" className="text-xl font-semibold">Baseline vs adapted model</h2>

      <p className="mt-4 text-xs text-muted-foreground">Examples</p>
      <div className="mt-1 flex flex-wrap gap-2">
        {EXAMPLES.map((e) => (
          <button
            key={e.label}
            type="button"
            onClick={() => { setText(e.text); run(e.text); }}
            className="rounded-full border border-border px-3 py-1.5 text-xs hover:border-primary hover:text-primary"
          >
            {e.label}
          </button>
        ))}
      </div>

      <label htmlFor="cd-text" className="mt-4 block text-xs text-muted-foreground">Message</label>
      <textarea
        id="cd-text"
        value={text}
        maxLength={2000}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder="e.g. Get FLAT 60% OFF on top brands this weekend only! Shop now at myntr.it/sale"
        className="mt-1 w-full border border-border bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
      />
      <div className="mt-3 flex flex-wrap items-center gap-4">
        <div role="radiogroup" aria-label="Classifier" className="inline-flex border border-border">
          {CLASSIFIERS.map((c) => (
            <button
              key={c.id}
              role="radio"
              aria-checked={classifier === c.id}
              onClick={() => { setClassifier(c.id); if (text.trim()) run(text, c.id); }}
              className={cn("px-3 py-2 text-sm", classifier === c.id ? "bg-primary text-primary-foreground" : "text-muted-foreground")}
            >
              {c.label}
            </button>
          ))}
        </div>
        <Button onClick={() => run()} disabled={busy || !text.trim()}>
          {busy ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Comparing…</> : "Compare"}
        </Button>
      </div>
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

      {pair && (
        <>
          <div
            className={cn(
              "mt-5 rounded-lg border px-4 py-3 text-sm",
              changed ? "border-primary/50 bg-primary/10" : "border-border bg-muted/40",
            )}
            role="status"
          >
            {changed ? (
              <>
                <b>Decision changed:</b> baseline <b>{pair.base.label.toUpperCase()}</b> (
                {pair.base.spam_probability.toFixed(3)}) → adapted <b>{pair.adapted.label.toUpperCase()}</b> (
                {pair.adapted.spam_probability.toFixed(3)}).
              </>
            ) : (
              <>
                <b>Both models: {pair.base.label.toUpperCase()}</b> ({pair.base.spam_probability.toFixed(3)} → {pair.adapted.spam_probability.toFixed(3)})
              </>
            )}
          </div>
          <div className="mt-4 grid items-stretch gap-4 lg:grid-cols-[1fr_auto_1fr]">
            <ResultCard title="Baseline" subtitle="Trained on UK SMS (UCI)" result={pair.base} />
            <div className="hidden items-center justify-center lg:flex" aria-hidden>
              <ArrowRight className="h-6 w-6 text-muted-foreground" />
            </div>
            <ResultCard title="Adapted" subtitle="UK SMS + 40% labelled Indian SMS" result={pair.adapted} />
          </div>
        </>
      )}
    </section>
  );
}
