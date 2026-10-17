"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getCaptchaChallenge } from "@/lib/api/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface CaptchaFieldProps {
  answer: string;
  onAnswerChange: (value: string) => void;
  /** Called with the current challenge token whenever a new challenge is fetched. */
  onTokenChange: (token: string) => void;
  error?: string;
  disabled?: boolean;
  /** Changing this value fetches a fresh challenge (e.g. after a failed submit). */
  refreshKey?: number;
}

/**
 * A real challenge-response widget, not a placeholder: the question and
 * token come from the backend's own HMAC-signed CAPTCHA
 * (app_service/core/captcha.py), verified server-side on submit. There is
 * no client-side "correct answer" hidden anywhere in this component.
 */
export function CaptchaField({ answer, onAnswerChange, onTokenChange, error, disabled, refreshKey = 0 }: CaptchaFieldProps) {
  const [question, setQuestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLocal, setIsLocal] = useState(false);
  useEffect(() => setIsLocal(["localhost", "127.0.0.1"].includes(window.location.hostname)), []);

  const fetchChallenge = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      // A sleeping or just-started server can fail the first request; retry
      // briefly before showing an error.
      let challenge;
      for (let attempt = 0; ; attempt++) {
        try {
          challenge = await getCaptchaChallenge();
          break;
        } catch (e) {
          if (attempt >= 2) throw e;
          await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
        }
      }
      setQuestion(challenge.question);
      onTokenChange(challenge.token);
      onAnswerChange("");
    } catch {
      setQuestion(null);
      setLoadError("Couldn't reach the ScamGuard server. Press the refresh button to try again.");
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchChallenge();
  }, [fetchChallenge, refreshKey]);

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground">
        Verification
      </label>
      <div className="flex items-center gap-2">
        <div aria-live="polite" className="flex h-10 flex-1 items-center rounded-md border border-border bg-muted px-3 text-sm">
          {isLoading ? "Loading challenge..." : loadError || question || ""}
        </div>
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={fetchChallenge}
          disabled={disabled || isLoading}
          aria-label="Get a new challenge"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
        </Button>
      </div>
      {loadError && isLocal && (
        <p role="alert" className="text-xs text-muted-foreground">
          Running ScamGuard on your computer? The backend server isn&apos;t running. Stop this window and start both parts
          with <code className="rounded bg-muted px-1">./start.sh</code> from the project folder (Windows:{" "}
          <code className="rounded bg-muted px-1">start_all.bat</code>), then open http://localhost:3000.
        </p>
      )}
      <Input
        aria-label="Verification answer"
        value={answer}
        onChange={(e) => onAnswerChange(e.target.value)}
        placeholder="Your answer"
        error={error}
        disabled={disabled || isLoading || !question}
        inputMode="numeric"
      />
    </div>
  );
}
