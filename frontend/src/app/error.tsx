"use client";

import { useEffect } from "react";
import { AlertOctagon, RefreshCcw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error(error);
  }, [error]);

  return (
    <html>
      <body>
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-4 text-center text-foreground">
          <div className="flex h-16 w-16 items-center justify-center border-2 border-destructive text-destructive">
            <AlertOctagon className="h-8 w-8" />
          </div>

          <div className="max-w-md space-y-2">
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">Error</p>
            <h1 className="font-sans text-3xl font-semibold tracking-tight">Something went wrong</h1>
            <p className="text-sm text-muted-foreground">
              An unexpected error occurred. You can try again, or head back to the dashboard.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button onClick={reset} size="lg">
              <RefreshCcw className="mr-2 h-4 w-4" />
              Try again
            </Button>
            <Link href="/">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                <Home className="mr-2 h-4 w-4" />
                Return home
              </Button>
            </Link>
          </div>
        </div>
      </body>
    </html>
  );
}
