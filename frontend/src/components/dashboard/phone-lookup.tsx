"use client";

import { useState, type FormEvent } from "react";
import { Phone } from "lucide-react";
import { lookupPhone, type PhoneLookupResult } from "@/lib/api/messages";
import { ApiError } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatDate, truncate, verdictLabel } from "@/lib/utils";

/** "Have I seen this number before?" -- searches only the user's own scans. */
export function PhoneLookup() {
  const [number, setNumber] = useState("");
  const [result, setResult] = useState<PhoneLookupResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (number.replace(/\D/g, "").length < 6) {
      setError("Enter a phone number with at least 6 digits.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      setResult(await lookupPhone(number));
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Lookup failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="console-panel min-w-0">
      <CardHeader>
        <p className="console-kicker mb-2">Number check</p>
        <CardTitle>Have I seen this number?</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <form onSubmit={submit} className="flex gap-2">
          <div className="flex-1">
            <Input aria-label="Phone number" placeholder="e.g. +91 98765 43210" value={number} onChange={(e) => setNumber(e.target.value)} inputMode="tel" />
          </div>
          <Button type="submit" isLoading={loading}>
            <Phone className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Check
          </Button>
        </form>
        {error && <p className="text-xs text-destructive">{error}</p>}
        {result && (
          <div className="space-y-2 text-sm">
            <p>
              <span className="font-mono">{result.number}</span>{" "}
              {result.seen_count === 0 ? (
                <span className="text-muted-foreground">has not appeared in any of your scans.</span>
              ) : (
                <span>
                  appeared in <strong>{result.seen_count}</strong> of your scans,{" "}
                  <strong className={result.flagged_count ? "text-destructive" : ""}>{result.flagged_count}</strong> flagged as suspicious.
                </span>
              )}
            </p>
            {!result.is_valid_indian_mobile && (
              <p className="text-xs text-amber-600 dark:text-amber-400">Not a standard 10-digit Indian mobile number.</p>
            )}
            {result.scans.length > 0 && (
              <ul className="divide-y divide-border rounded-sm border border-border">
                {result.scans.map((s) => (
                  <li key={s.id} className="px-3 py-2">
                    <p className="truncate text-xs text-foreground">{truncate(s.preview, 80)}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {verdictLabel(s.verdict as never)} · {s.created_at ? formatDate(s.created_at) : ""}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-[11px] text-muted-foreground">Searches only your own saved scans; no external phone database is used.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
