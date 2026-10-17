/** Review-queue logic for the scam flashcards. Pure functions, so the
 * behaviour is unit-tested (src/lib/__tests__/flashcards.test.ts). */

export interface Deck {
  queue: string[];   // card ids still to answer, in order
  known: string[];   // answered "Got it"
  missed: string[];  // answered "Review again" at least once
}

export const REVIEW_GAP = 3;

export function newDeck(ids: string[], shuffle: (ids: string[]) => string[] = (x) => x): Deck {
  return { queue: shuffle([...new Set(ids)]), known: [], missed: [] };
}

/** "Got it": the card leaves the queue. */
export function markKnown(d: Deck): Deck {
  const [id, ...rest] = d.queue;
  if (id === undefined) return d;
  return { queue: rest, known: d.known.includes(id) ? d.known : [...d.known, id], missed: d.missed };
}

/** "Review again": the card comes back a few cards later (or last, if fewer remain). */
export function markAgain(d: Deck, gap = REVIEW_GAP): Deck {
  const [id, ...rest] = d.queue;
  if (id === undefined) return d;
  const at = Math.min(gap, rest.length);
  return { queue: [...rest.slice(0, at), id, ...rest.slice(at)], known: d.known, missed: d.missed.includes(id) ? d.missed : [...d.missed, id] };
}

/** Keep a saved deck only if it still matches the current cards. */
export function restoreDeck(saved: unknown, ids: string[]): Deck | null {
  if (typeof saved !== "object" || saved === null) return null;
  const s = saved as Partial<Deck>;
  const valid = new Set(ids);
  const clean = (v: unknown) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && valid.has(x)) : null);
  const queue = clean(s.queue), known = clean(s.known), missed = clean(s.missed);
  if (!queue || !known || !missed) return null;
  const covered = new Set([...queue, ...known]);
  const missing = ids.filter((id) => !covered.has(id));
  return { queue: [...new Set(queue), ...missing], known: [...new Set(known)], missed: [...new Set(missed)] };
}

export function shuffled<T>(items: T[], random: () => number = Math.random): T[] {
  const a = [...items];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    const tmp = a[i] as T;
    a[i] = a[j] as T;
    a[j] = tmp;
  }
  return a;
}
