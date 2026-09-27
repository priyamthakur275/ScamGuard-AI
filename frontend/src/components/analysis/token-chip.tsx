import type { FeatureContribution } from "@/types";

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
      {contribution.token.replace(/^__|__$/g, "")}
    </span>
  );
}
