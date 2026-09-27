import { apiRequest } from "@/lib/api/client";
import type { CaseDetail, CaseSummary, CaseTimelineEntry } from "@/types/case";

export interface CreateCasePayload {
  title: string;
  description?: string;
  severity?: string;
  scan_ids?: string[];
}

export function createCase(payload: CreateCasePayload): Promise<CaseSummary> {
  return apiRequest<CaseSummary>("/cases", { method: "POST", body: payload });
}

export function listCases(status?: string): Promise<CaseSummary[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<CaseSummary[]>(`/cases${query}`, { method: "GET" });
}

export function getCase(caseId: string): Promise<CaseDetail> {
  return apiRequest<CaseDetail>(`/cases/${caseId}`, { method: "GET" });
}

export function updateCase(
  caseId: string,
  payload: Partial<{ title: string; description: string; severity: string; status: string }>,
): Promise<CaseSummary> {
  return apiRequest<CaseSummary>(`/cases/${caseId}`, { method: "PATCH", body: payload });
}

export function linkScanToCase(caseId: string, predictionId: string): Promise<CaseSummary> {
  return apiRequest<CaseSummary>(`/cases/${caseId}/scans`, {
    method: "POST",
    body: { prediction_id: predictionId },
  });
}

export function unlinkScanFromCase(caseId: string, predictionId: string): Promise<CaseSummary> {
  return apiRequest<CaseSummary>(`/cases/${caseId}/scans/${predictionId}`, { method: "DELETE" });
}

export function addCaseNote(caseId: string, content: string): Promise<CaseTimelineEntry> {
  return apiRequest<CaseTimelineEntry>(`/cases/${caseId}/notes`, {
    method: "POST",
    body: { content },
  });
}
