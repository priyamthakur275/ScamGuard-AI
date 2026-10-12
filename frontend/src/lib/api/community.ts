import { apiRequest } from "@/lib/api/client";

export type IndicatorType = "phone" | "url" | "upi" | "email";

export interface CommunityLookup {
  indicator_type: IndicatorType;
  indicator_value: string;
  report_count: number;
  last_reported_at: string | null;
  categories: Record<string, number>;
  created?: boolean;
}

export function reportIndicator(indicator_type: IndicatorType, value: string, category?: string | null): Promise<CommunityLookup> {
  return apiRequest<CommunityLookup>("/community/reports", {
    method: "POST",
    body: { indicator_type, value, category: category ?? null },
  });
}

export function lookupIndicator(indicator_type: IndicatorType, value: string): Promise<CommunityLookup> {
  const q = new URLSearchParams({ indicator_type, value });
  return apiRequest<CommunityLookup>(`/community/lookup?${q}`, { auth: false });
}
