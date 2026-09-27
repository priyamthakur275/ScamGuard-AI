import { apiRequest } from "./client";

export interface TransformResult {
  transform_code: string;
  transform_label: string;
  transformed_text: string;
  base_verdict: string;
  base_probability: number;
  transformed_verdict: string;
  transformed_probability: number;
  verdict_changed: boolean;
  probability_delta: number;
  stability: "stable" | "changed" | "significantly_changed" | "not_applicable";
}

export interface BaseMessageReport {
  message_id: string;
  category: "scam" | "benign_scam_vocab";
  base_text: string;
  base_verdict: string;
  base_probability: number;
  transform_results: TransformResult[];
}

export async function runRobustnessTest(): Promise<BaseMessageReport[]> {
  return apiRequest<BaseMessageReport[]>("/admin/robustness-test", { method: "POST" });
}
