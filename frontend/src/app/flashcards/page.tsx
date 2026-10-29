"use client";

import { PublicShell } from "@/components/layout/public-shell";
import { HowToCards } from "@/components/landing/how-to-cards";

export default function FlashcardsPage() {
  return (
    <PublicShell>
      <div className="-mx-4 -my-10 md:-mx-6 [&_section]:border-t-0">
        <HowToCards />
      </div>
    </PublicShell>
  );
}
