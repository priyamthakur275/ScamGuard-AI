import { Globe, Mail, Phone, Wallet, Link2, Bitcoin, IndianRupee, Landmark, Calendar, Building2 } from "lucide-react";
import { motion } from "framer-motion";

interface EntityHighlightsProps {
  entities: {
    urls?: string[];
    emails?: string[];
    phones?: string[];
    upi_ids?: string[];
    shortened_links?: string[];
    crypto_wallets?: string[];
    payment_amounts?: string[];
    bank_references?: string[];
    dates?: string[];
    organizations?: string[];
  } | null | undefined;
}

// bank_references (IFSC codes / account numbers) are masked in the UI --
// the full value is real, computed evidence and stays available in the
// underlying data, but there's no reason to display someone's full
// account number in a shared/screenshotted result when the last few
// characters are enough to recognize it as evidence.
function maskSensitive(value: string): string {
  if (value.length <= 4) return value;
  return "•".repeat(Math.max(value.length - 4, 4)) + value.slice(-4);
}

const ENTITY_CONFIG = [
  { key: "urls", label: "URLs", icon: Globe },
  { key: "emails", label: "Emails", icon: Mail },
  { key: "phones", label: "Phones", icon: Phone },
  { key: "upi_ids", label: "UPI IDs", icon: Wallet },
  { key: "shortened_links", label: "Shortened Links", icon: Link2 },
  { key: "crypto_wallets", label: "Crypto Wallets", icon: Bitcoin },
  { key: "payment_amounts", label: "Payment Amounts", icon: IndianRupee },
  { key: "bank_references", label: "Bank References", icon: Landmark, sensitive: true },
  { key: "dates", label: "Dates", icon: Calendar },
  { key: "organizations", label: "Organizations", icon: Building2 },
] as const;

export function EntityHighlights({ entities }: EntityHighlightsProps) {
  if (!entities) return null;

  const activeEntities = ENTITY_CONFIG.filter(
    (config) => entities[config.key as keyof typeof entities]?.length
  );

  if (activeEntities.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <h4 className="font-mono text-xs font-semibold uppercase tracking-wide text-foreground">Observed entities</h4>
      <div className="flex flex-wrap gap-2">
        {activeEntities.map((config) => {
          const items = entities[config.key as keyof typeof entities] ?? [];
          const Icon = config.icon;
          const isSensitive = "sensitive" in config && config.sensitive;
          return items.map((item, i) => {
            const display = isSensitive ? maskSensitive(item) : item;
            return (
              <motion.span
                key={`${config.key}-${i}`}
                whileHover={{ y: -1 }}
                title={isSensitive ? `${config.label} (masked)` : config.label}
                className="inline-flex items-center gap-1.5 border border-border bg-muted px-2.5 py-1.5 font-mono text-xs text-foreground transition-colors cursor-default"
              >
                <Icon className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                {display.length > 40 ? display.slice(0, 37) + "..." : display}
              </motion.span>
            );
          });
        })}
      </div>
    </div>
  );
}
