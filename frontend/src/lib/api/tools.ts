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
export const checkPaymentScreenshot = (file: File) => upload<ToolResult>("/tools/payment-screenshot", file);
export const checkFile = (file: File) => upload<ToolResult>("/tools/file", file);
export const getPayReasons = () => apiRequest<{ id: string; label: string }[]>("/tools/pay-reasons", { auth: false });
export const payCheck = (body: { upi_id: string; payee_name: string; expected_name: string; amount: string; reason: string }) =>
  apiRequest<ToolResult>("/tools/pay-check", { method: "POST", body, auth: false });
export const whatIf = (text: string) => apiRequest<WhatIfResult>("/tools/what-if", { method: "POST", body: { text }, auth: false });

export interface TimelineMessage { index: number; sender: string; text: string; risk_score: number; verdict: string; stages: string[]; signs: string[] }
export interface TimelineResult {
  messages: TimelineMessage[];
  stage_first_seen: Record<"hook" | "pressure" | "ask" | "cashout", number | null>;
  stages_reached: string[];
  turning_point: number | null;
  first_high_risk: number | null;
  suspected_sender: string | null;
  overall: { risk_score: number; verdict: string; classifier_probability: number };
  summary: string;
  note: string;
}
export const checkTimeline = (text: string) => apiRequest<TimelineResult>("/tools/timeline", { method: "POST", body: { text }, auth: false });

export interface XrayFeature { feature: string; push: number }
export interface ModelXrayResult {
  bias: number;
  words_up: XrayFeature[];
  words_down: XrayFeature[];
  words_up_total: number;
  words_down_total: number;
  words_up_count: number;
  words_down_count: number;
  char_total: number;
  char_count: number;
  char_examples: XrayFeature[];
  logit: number;
  probability: number;
  active_features: number;
  vocabulary: number;
  model: string;
}
export const modelXray = (text: string) => apiRequest<ModelXrayResult>("/tools/model-xray", { method: "POST", body: { text }, auth: false });

