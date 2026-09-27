"use client";

import { useEffect } from "react";
import { AlertOctagon } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardError({
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
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-destructive/30 bg-destructive/5 py-16 text-center">
      <AlertOctagon className="h-8 w-8 text-destructive" />
      <h2 className="text-lg font-semibold text-foreground">This page failed to load</h2>
      <p className="max-w-sm text-sm text-muted-foreground">
        Something went wrong while loading this page. Try again, or navigate elsewhere using the sidebar.
      </p>
      <Button onClick={reset} variant="outline">
        Try again
      </Button>
    </div>
  );
}
