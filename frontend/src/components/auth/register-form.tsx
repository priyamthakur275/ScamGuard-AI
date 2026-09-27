"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/auth-context";
import { ApiError } from "@/lib/api/client";
import { registerSchema } from "@/lib/validation/auth-schemas";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { CaptchaField } from "@/components/auth/captcha-field";
import { RefreshCw } from "lucide-react";

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [captchaToken, setCaptchaToken] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isWakingServer, setIsWakingServer] = useState(false);
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  const [captchaRefreshKey, setCaptchaRefreshKey] = useState(0);

  // Proactively wake up backend from standby on page mount
  useEffect(() => {
    fetch("/backend-api/api/v1/health").catch(() => {});
  }, []);

  // Track elapsed time during submission
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSubmitting) {
      interval = setInterval(() => {
        setSecondsElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      setSecondsElapsed(0);
    }
    return () => clearInterval(interval);
  }, [isSubmitting]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) return;
    setFormError(null);

    const result = registerSchema.safeParse({ email, password, confirmPassword });
    if (!result.success) {
      const errors: Record<string, string> = {};
      for (const issue of result.error.issues) {
        errors[String(issue.path[0])] = issue.message;
      }
      setFieldErrors(errors);
      return;
    }
    if (!captchaToken || !captchaAnswer.trim()) {
      setFieldErrors({ captcha: "Please answer the verification question." });
      return;
    }
    setFieldErrors({});
    setIsSubmitting(true);
    setIsWakingServer(false);

    // Show server wake-up notice if request takes > 2.5s
    const wakeTimer = setTimeout(() => {
      setIsWakingServer(true);
    }, 2500);

    try {
      await register({
        email: result.data.email,
        password: result.data.password,
        captcha_token: captchaToken,
        captcha_answer: captchaAnswer,
      });
      router.push("/dashboard");
    } catch (error) {
      // A submitted answer is spent: always offer a fresh challenge, so an
      // expired or wrong one can't leave the form unanswerable.
      setCaptchaRefreshKey((k) => k + 1);
      if (error instanceof ApiError) {
        setFormError(
          error.errorCode === "CONFLICT"
            ? "An account with this email already exists. Try signing in instead."
            : error.errorCode === "INVALID_CAPTCHA"
              ? "That verification answer wasn't correct. Answer the new challenge below."
              : error.message,
        );
      } else {
        setFormError("Something went wrong while contacting the server. Try again.");
      }
    } finally {
      clearTimeout(wakeTimer);
      setIsWakingServer(false);
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">
      {formError && <Alert variant="error">{formError}</Alert>}

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={fieldErrors.email}
        placeholder="you@example.com"
        disabled={isSubmitting}
      />

      <Input
        label="Password"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={fieldErrors.password}
        placeholder="At least 8 characters"
        hint="Must contain at least 8 characters, one number, and one uppercase letter."
        disabled={isSubmitting}
      />

      <Input
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        error={fieldErrors.confirmPassword}
        placeholder="Repeat password"
        disabled={isSubmitting}
      />

      <CaptchaField
        answer={captchaAnswer}
        onAnswerChange={setCaptchaAnswer}
        onTokenChange={setCaptchaToken}
        refreshKey={captchaRefreshKey}
        error={fieldErrors.captcha}
        disabled={isSubmitting}
      />

      <div className="flex flex-col gap-2 mt-1">
        <Button type="submit" isLoading={isSubmitting} className="w-full" size="lg">
          {isWakingServer
            ? `Connecting to server (${secondsElapsed}s)...`
            : isSubmitting
              ? "Creating account..."
              : "Create account"}
        </Button>


      </div>

      {isWakingServer && (
        <div className="border border-primary/25 bg-primary/10 p-3 text-center">
          <p className="font-mono text-xs font-medium uppercase tracking-wide text-primary">
            Waiting for the server — {secondsElapsed}s elapsed
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            The request is still in progress. Wait for confirmation before trying again.
          </p>
        </div>
      )}

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
