import { apiRequest, ApiError } from "@/lib/api/client";
import type { AnalysisResult } from "@/types";

export function getHistory(skip = 0, limit = 50): Promise<AnalysisResult[]> {
  return apiRequest<AnalysisResult[]>(`/messages/history?skip=${skip}&limit=${limit}`);
}
export function clearHistory(): Promise<void> {
  return apiRequest<void>("/messages/history", { method: "DELETE" });
}
export function deleteMessage(id: string): Promise<void> {
  return apiRequest<void>(`/messages/${id}`, { method: "DELETE" });
}
export function submitFeedback(predictionId: string, isAccurate: boolean): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>(`/messages/${predictionId}/feedback`, {
    method: "PATCH", body: { is_accurate: isAccurate },
  });
}
export function scanFile(file: File | null, text: string | null, inputType: string): Promise<AnalysisResult> {
  const body = new FormData();
  body.append("input_type", inputType);
  if (file) body.append("file", file);
  if (text) body.append("text", text);
  return apiRequest<AnalysisResult>("/messages/scan", { method: "POST", body });
}
export { ApiError };

export interface PhoneLookupScan {
  id: string;
  verdict: string;
  threat_level: string | null;
  scam_category: string | null;
  created_at: string | null;
  preview: string;
}

export interface PhoneLookupResult {
  number: string;
  is_valid_indian_mobile: boolean;
  seen_count: number;
  flagged_count: number;
  first_seen: string | null;
  last_seen: string | null;
  scans: PhoneLookupScan[];
}

export function lookupPhone(number: string): Promise<PhoneLookupResult> {
  return apiRequest<PhoneLookupResult>(`/messages/lookup/phone?number=${encodeURIComponent(number)}`, { method: "GET" });
}
