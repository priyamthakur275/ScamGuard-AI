import { ShieldCheck } from "lucide-react";

interface RecommendedActionsProps {
  actions: string[] | null | undefined;
}

export function RecommendedActions({ actions }: RecommendedActionsProps) {
  if (!actions || actions.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-sm font-semibold text-foreground">Recommended Actions</h4>
      <ul className="flex flex-col gap-2">
        {actions.map((action, i) => (
          <li key={i} className="flex items-start gap-2.5 rounded-md border border-border/50 bg-muted/30 px-3 py-2.5">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            <span className="text-sm text-foreground">{action}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
