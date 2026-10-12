import type { FeatureContribution } from "@/types";

// "__url__" and "__num__" are the preprocessor's placeholders for any link
// or number; show them as plain words.
function displayToken(token: string): string {
  return token.replace(/__url__/g, "link").replace(/__num__/g, "number");
}

export function TokenChip({
  contribution,
  maxWeight,
}: {
  contribution: FeatureContribution;
  maxWeight: number;
}) {
  const intensity = maxWeight > 0 ? Math.min(contribution.weight / maxWeight, 1) : 0;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground"
      style={{
        backgroundColor: `hsl(var(--risk-high) / ${0.08 + intensity * 0.22})`,
      }}
      title={`Contribution weight: ${contribution.weight.toFixed(4)}`}
    >
      {displayToken(contribution.token)}
    </span>
  );
}
