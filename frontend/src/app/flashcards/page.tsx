"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BookOpen, Check, ExternalLink, Loader2, RotateCcw, Undo2 } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { getFlashcards, type Flashcard } from "@/lib/api/public";
import { markAgain, markKnown, newDeck, restoreDeck, shuffled, type Deck } from "@/lib/flashcards";
import { cn, scamCategoryLabel } from "@/lib/utils";

const STORE = "scamguard.flashcards.v1";
const STAGE: Record<string, string> = { hook: "Hook", pressure: "Pressure", ask: "Ask", cashout: "Cash-out" };

function load(): unknown {
  try { return JSON.parse(window.localStorage.getItem(STORE) ?? "null"); } catch { return null; }
}
function save(d: Deck) {
  try { window.localStorage.setItem(STORE, JSON.stringify(d)); } catch { /* storage unavailable: progress lasts this visit */ }
}

export default function FlashcardsPage() {
  const [cards, setCards] = useState<Flashcard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  const fetchCards = useCallback(async () => {
    setError(null);
    try {
      const res = await getFlashcards();
      setCards(res.cards);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the flashcards.");
    }
  }, []);
  useEffect(() => { void fetchCards(); }, [fetchCards]);

  const visible = useMemo(() => (cards ?? []).filter((c) => filter === "all" || c.scam_type === filter), [cards, filter]);
  const byId = useMemo(() => new Map((cards ?? []).map((c) => [c.id, c])), [cards]);
  const types = useMemo(() => [...new Set((cards ?? []).map((c) => c.scam_type))].sort(), [cards]);

  useEffect(() => {
    if (!cards) return;
    const ids = visible.map((c) => c.id);
    const saved = filter === "all" ? restoreDeck(load(), ids) : null;
    setDeck(saved ?? newDeck(ids, shuffled));
    setFlipped(false);
  }, [cards, visible, filter]);

  const update = (next: Deck) => {
    setDeck(next);
    setFlipped(false);
    if (filter === "all") save(next);
  };
  const restart = () => update(newDeck(visible.map((c) => c.id), shuffled));

  const currentId = deck?.queue[0];
  const current = currentId !== undefined ? byId.get(currentId) : undefined;
  const total = visible.length;
  const done = deck ? deck.known.filter((id) => visible.some((c) => c.id === id)).length : 0;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current || (e.target as HTMLElement)?.closest("input, textarea, select")) return;
      if (e.key === " " || e.key === "Enter") { e.preventDefault(); setFlipped((f) => !f); }
      if (flipped && deck && (e.key === "ArrowRight" || e.key.toLowerCase() === "k")) update(markKnown(deck));
      if (flipped && deck && (e.key === "ArrowLeft" || e.key.toLowerCase() === "r")) update(markAgain(deck));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <PublicShell>
      <div className="mx-auto max-w-2xl px-4 py-10 sm:py-14">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Scam flashcards</h1>
        <p className="mt-2 text-muted-foreground">
          Real scam patterns from ScamGuard&apos;s cited library. Read the message, decide what&apos;s wrong, then flip the card.
        </p>

        {error && (
          <div role="alert" className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
            <button type="button" onClick={fetchCards} className="rounded-lg border border-destructive/40 px-3 py-1">Try again</button>
          </div>
        )}
        {!cards && !error && (
          <p className="mt-10 flex items-center gap-2 text-muted-foreground" role="status"><Loader2 className="h-4 w-4 animate-spin" /> Loading cards…</p>
        )}

        {cards && deck && (
          <>
            <div className="mt-6 flex flex-wrap items-center gap-2">
              <label className="text-sm text-muted-foreground" htmlFor="fc-filter">Scam type</label>
              <select id="fc-filter" value={filter} onChange={(e) => setFilter(e.target.value)}
                className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
                <option value="all">All ({cards.length})</option>
                {types.map((t) => <option key={t} value={t}>{scamCategoryLabel(t)}</option>)}
              </select>
              <span className="ml-auto text-sm text-muted-foreground" aria-live="polite">{done} / {total} learnt</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden>
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${total ? (done / total) * 100 : 0}%` }} />
            </div>

            {current ? (
              <article className="mt-6 rounded-2xl border border-border bg-card p-5 sm:p-6" aria-live="polite">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{flipped ? "The trick" : "Would you trust this?"}</p>
                {!flipped ? (
                  <>
                    <blockquote className="mt-3 whitespace-pre-wrap rounded-xl bg-muted/60 p-4 text-[15px] leading-relaxed">{current.message}</blockquote>
                    <button type="button" onClick={() => setFlipped(true)}
                      className="mt-5 w-full rounded-xl bg-primary px-5 py-3 font-medium text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                      Show the answer
                    </button>
                    <p className="mt-2 text-center text-xs text-muted-foreground">Space or Enter flips the card</p>
                  </>
                ) : (
                  <div className="mt-3 space-y-4 text-sm">
                    <p className="text-lg font-semibold">{current.title}</p>
                    <div>
                      <p className="font-medium">Warning signs</p>
                      <ul className="mt-1 space-y-1.5">
                        {current.tactics.map((t) => (
                          <li key={t.id}>
                            <span className="mr-1 rounded-full bg-destructive/15 px-2 py-0.5 text-xs text-destructive">{STAGE[t.stage] ?? "Sign"}</span>
                            <span className="font-medium">{t.label}</span>{t.why && <span className="text-muted-foreground">: {t.why}</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <p><span className="font-medium">What happens next: </span>{current.what_happens_next}</p>
                    {current.actions.length > 0 && (
                      <div>
                        <p className="font-medium">What to do</p>
                        <ul className="mt-1 list-disc space-y-1 pl-5">{current.actions.map((a) => <li key={a}>{a}</li>)}</ul>
                      </div>
                    )}
                    <a href={current.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary underline">
                      Source: {current.source_name} <ExternalLink className="h-3 w-3" aria-hidden />
                    </a>
                    <div className="grid grid-cols-2 gap-2 pt-2">
                      <button type="button" onClick={() => update(markAgain(deck))}
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-4 py-3 font-medium hover:border-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                        <Undo2 className="h-4 w-4" aria-hidden /> Review again
                      </button>
                      <button type="button" onClick={() => update(markKnown(deck))}
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 font-medium text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                        <Check className="h-4 w-4" aria-hidden /> Got it
                      </button>
                    </div>
                    <p className="text-center text-xs text-muted-foreground">Keys: → or K = got it, ← or R = review again</p>
                  </div>
                )}
              </article>
            ) : (
              <div className="mt-6 rounded-2xl border border-border bg-card p-6 text-center">
                <BookOpen className="mx-auto h-8 w-8 text-primary" aria-hidden />
                <p className="mt-2 text-lg font-semibold">{total === 0 ? "No cards for this scam type." : "All cards learnt!"}</p>
                {deck.missed.length > 0 && total > 0 && (
                  <p className="mt-1 text-sm text-muted-foreground">You reviewed {deck.missed.length} card{deck.missed.length > 1 ? "s" : ""} more than once.</p>
                )}
                <button type="button" onClick={restart} className={cn("mt-4 inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm hover:border-primary")}>
                  <RotateCcw className="h-4 w-4" aria-hidden /> Start again
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </PublicShell>
  );
}
