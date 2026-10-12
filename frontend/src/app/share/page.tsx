"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PublicShell } from "@/components/layout/public-shell";
import { QuickCheck } from "@/components/landing/quick-check";
import { useLanguage } from "@/lib/i18n/language-context";

/** Target of the installed app's share sheet (manifest share_target):
 * WhatsApp/SMS -> Share -> ScamGuard lands here with ?text=...&url=... */
function SharedCheck() {
  const params = useSearchParams();
  const { t } = useLanguage();
  const text = [params.get("title"), params.get("text"), params.get("url")]
    .filter((v): v is string => Boolean(v && v.trim()))
    .filter((v, i, all) => all.indexOf(v) === i)
    .join("\n")
    .slice(0, 2000);
  return <QuickCheck initialText={text} autoRun heading={text ? t("share.checking") : t("share.empty")} />;
}

export default function SharePage() {
  return (
    <PublicShell>
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
        <SharedCheck />
      </Suspense>
    </PublicShell>
  );
}
