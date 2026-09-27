import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ className, label = "Loading" }: { className?: string; label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center">
      <Loader2 className={cn("h-6 w-6 animate-spin text-primary", className)} aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function FullPageSpinner() {
  return (
    <div className="flex h-[60vh] w-full items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  );
}
