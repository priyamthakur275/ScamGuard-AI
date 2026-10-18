/** Tiny in-memory cache for read-only API calls (history, analytics), so
 * moving between dashboard pages is instant. Entries expire after a short
 * time and are cleared on any write (scan, delete, feedback) and on every
 * sign-in or sign-out, so a page never shows stale or another user's data.
 * Concurrent calls for the same key share one request. */

type Entry = { at: number; value?: unknown; pending?: Promise<unknown> };
const store = new Map<string, Entry>();
export const CACHE_TTL_MS = 30_000;

export function cached<T>(key: string, load: () => Promise<T>, ttl = CACHE_TTL_MS, now: () => number = Date.now): Promise<T> {
  const hit = store.get(key);
  if (hit?.pending) return hit.pending as Promise<T>;
  if (hit && "value" in hit && now() - hit.at < ttl) return Promise.resolve(hit.value as T);
  const pending = load().then(
    (value) => { store.set(key, { at: now(), value }); return value; },
    (err) => { store.delete(key); throw err; },
  );
  store.set(key, { at: now(), pending });
  return pending;
}

/** Drop every entry whose key starts with one of the prefixes (all if none). */
export function invalidate(...prefixes: string[]): void {
  for (const key of [...store.keys()]) {
    if (prefixes.length === 0 || prefixes.some((p) => key.startsWith(p))) store.delete(key);
  }
}
