"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, RotateCcw, ShieldAlert, ShieldCheck, Trophy, XCircle } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { Button, buttonVariants } from "@/components/ui/button";
import { TRAINER_ITEMS, type TrainerItem } from "@/lib/trainer/questions";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/language-context";

const ROUND = 8;
const BEST_KEY = "scamguard_trainer_best";

function shuffle<T>(items: T[]): T[] {
  const a = [...items];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j] as T, a[i] as T];
  }
  return a;
}

function rank(score: number): string {
  if (score === ROUND) return "Scam Spotter — perfect round!";
  if (score >= ROUND - 2) return "Sharp eye — scammers would struggle with you.";
  if (score >= ROUND / 2) return "Getting there — play again to learn the red flags.";
  return "Scammers count on this — try another round.";
}

export default function TrainerPage() {
  const { t } = useLanguage();
  const [seed, setSeed] = useState(0);
  const round = useMemo<TrainerItem[]>(() => shuffle(TRAINER_ITEMS).slice(0, ROUND), [seed]); // eslint-disable-line react-hooks/exhaustive-deps
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<boolean[]>([]);
  const [best, setBest] = useState<number | null>(null);

  useEffect(() => {
    try {
      const v = localStorage.getItem(BEST_KEY);
      if (v) setBest(Number(v));
    } catch {
      /* storage unavailable: best score just isn't remembered */
    }
  }, []);

  const item = round[index];
  const answered = answers.length > index;
  const [finished, setFinished] = useState(false);
  const score = answers.filter((a, i) => a === round[i]?.isScam).length;

  function answer(saysScam: boolean) {
    if (answered) return;
    const next = [...answers, saysScam];
    setAnswers(next);
    if (next.length === ROUND) {
      const final = next.filter((a, i) => a === round[i]?.isScam).length;
      if (best === null || final > best) {
        setBest(final);
        try {
          localStorage.setItem(BEST_KEY, String(final));
        } catch {
          /* ignore */
        }
      }
    }
  }

  function restart() {
    setSeed((s) => s + 1);
    setIndex(0);
    setAnswers([]);
    setFinished(false);
  }

  return (
    <PublicShell>
      <p className="text-xs text-primary">{t("tr.kicker")}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">{t("tr.title")}</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        {t("tr.sub")}
      </p>

      <div className="mt-6 flex items-center gap-3">
        <div className="h-2 flex-1 bg-muted">
          <div className="h-2 bg-primary transition-all" style={{ width: `${(answers.length / ROUND) * 100}%` }} />
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          {Math.min(index + 1, ROUND)}/{ROUND} · {t("tr.score")} {score}
          {best !== null ? ` · ${t("tr.best")} ${best}` : ""}
        </span>
      </div>

      {item && !finished && (
        <section className="mt-6 border border-border p-5">
          <p className="text-xs text-muted-foreground">
            {item.channel} · from {item.from}
          </p>
          <p className="mt-3 border-l-2 border-primary/50 bg-muted/30 p-4 text-base leading-relaxed">{item.message}</p>

          {!answered ? (
            <div className="mt-5 grid grid-cols-2 gap-3">
              <Button variant="outline" onClick={() => answer(true)} className="h-12 border-destructive/50 text-destructive">
                <ShieldAlert className="mr-2 h-5 w-5" /> {t("tr.scam")}
              </Button>
              <Button variant="outline" onClick={() => answer(false)} className="h-12 border-emerald-500/50 text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="mr-2 h-5 w-5" /> {t("tr.safe")}
              </Button>
            </div>
          ) : (
            <div className="mt-5" role="status" aria-live="polite">
              {answers[index] === item.isScam ? (
                <p className="flex items-center gap-2 font-semibold text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-5 w-5" /> {t("tr.correct")} — {item.isScam ? t("tr.isScam") : t("tr.isSafe")}
                </p>
              ) : (
                <p className="flex items-center gap-2 font-semibold text-destructive">
                  <XCircle className="h-5 w-5" /> {t("tr.wrong")} — {item.isScam ? t("tr.isScam") : t("tr.isSafe")}
                </p>
              )}
              <p className="mt-2 text-sm">{item.lesson}</p>
              <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">
                {item.flags.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              <Button
                className="mt-4"
                onClick={() => (index === ROUND - 1 ? setFinished(true) : setIndex((i) => i + 1))}
              >
                {index === ROUND - 1 ? t("tr.see") : t("tr.next")}
              </Button>
            </div>
          )}
        </section>
      )}

      {finished && (
        <section className="mt-6 border border-border p-6 text-center">
          <Trophy className="mx-auto h-10 w-10 text-primary" />
          <p className="mt-3 text-4xl font-semibold tabular-nums">
            {score}/{ROUND}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">{rank(score)}</p>
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <Button onClick={restart}>
              <RotateCcw className="mr-1.5 h-4 w-4" /> {t("tr.again")}
            </Button>
            <a
              className={buttonVariants({ variant: "outline" })}
              href={`https://wa.me/?text=${encodeURIComponent(`I scored ${score}/${ROUND} on the ScamGuard scam-spotting test. Can you beat me? ${typeof window !== "undefined" ? window.location.origin : ""}/trainer`)}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {t("tr.challenge")}
            </a>
            <Link href="/#quick-check" className={cn(buttonVariants({ variant: "ghost" }))}>
              {t("tr.checkReal")}
            </Link>
          </div>
        </section>
      )}
    </PublicShell>
  );
}
