"use client";

import { PublicShell } from "@/components/layout/public-shell";
import { PlaybookList } from "@/components/playbooks/playbook-list";

export default function FlashcardsPage() {
  return (
    <PublicShell>
      <PlaybookList />
    </PublicShell>
  );
}
