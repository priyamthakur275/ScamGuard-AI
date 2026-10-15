import { apiRequest } from "@/lib/api/client";
import type { AnalysisResult } from "@/types";

export type FlagLevel = "danger" | "warning" | "info" | "ok";
export interface ToolFlag { level: FlagLevel; title: string; detail: string }
export interface ToolResult {
  risk: "high" | "medium" | "low";
  summary: string;
  flags: ToolFlag[];
  facts: Record<string, string | number>;
}
export type QrResult =
  | ({ kind: "upi"; content: string } & ToolResult)
  | { kind: "url" | "text"; content: string; analysis: AnalysisResult | null };

export interface WhatIfPart { label: string; phrase: string; score_alone: number; lift: number; drop: number }
export interface WhatIfResult { score: number; baseline: number | null; parts: WhatIfPart[]; redundant: boolean }

function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<T>(path, { method: "POST", body, auth: false });
}

export const checkQr = (file: File) => upload<QrResult>("/tools/qr", file);
export const checkFile = (file: File) => upload<ToolResult>("/tools/file", file);
export const getPayReasons = () => apiRequest<{ id: string; label: string }[]>("/tools/pay-reasons", { auth: false });
export const payCheck = (body: { upi_id: string; payee_name: string; expected_name: string; amount: string; reason: string }) =>
  apiRequest<ToolResult>("/tools/pay-check", { method: "POST", body, auth: false });
export const whatIf = (text: string) => apiRequest<WhatIfResult>("/tools/what-if", { method: "POST", body: { text }, auth: false });
