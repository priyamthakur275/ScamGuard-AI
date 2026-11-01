import { apiRequest } from "@/lib/api/client";
import type { AnalysisResult } from "@/types";

/** No-login text check; the server runs the real pipeline but stores nothing. */
export function quickCheck(text: string): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>("/public/quick-check", { method: "POST", body: { text }, auth: false });
}

export async function checkHealth(): Promise<boolean> {
  try {
    await apiRequest<unknown>("/health", { method: "GET", auth: false });
    return true;
  } catch {
    return false;
  }
}

export interface ScamTrends {
  days: number;
  total_scans: number;
  flagged_scans: number;
  flagged_rate: number;
  top_categories: { category: string; count: number }[];
  channels: { input_type: string; count: number }[];
  daily: { date: string; total: number; flagged: number }[];
  generated_at: string;
}

export function getTrends(days: 7 | 30): Promise<ScamTrends> {
  return apiRequest<ScamTrends>(`/public/trends?days=${days}`, { auth: false });
}

// ---------------------------------------------------------------- cross-domain spam study

export type CdClassifier = "logistic_regression" | "naive_bayes";
export type CdVersion = "baseline" | "adapted40";

export interface CdClassification {
  label: "spam" | "ham";
  spam_probability: number;
  model: {
    id: string;
    classifier: string;
    version: string;
    features: string;
    train_messages: number | null;
    seed: number | null;
    target_test_f1: number | null;
  };
  top_features: { feature: string; contribution: number }[];
}

export interface CdAdaptationRow {
  model: CdClassifier;
  feature: "word" | "char";
  target_fraction: number;
  B_f1_mean: number;
  B_f1_std: number;
  B_precision_mean: number;
  B_recall_mean: number;
  A_f1_mean: number;
}

export interface CdResults {
  seeds: number[];
  dataset_statistics: Record<string, string | number>[];
  within_vs_cross: { Model: string; Feature: string; "Test domain": string; Accuracy: number; Precision: number; Recall: number; "F1-score": number }[];
  adaptation_summary: CdAdaptationRow[];
  confusion_seed42: { "Evaluation setting": string; TN: number; FP: number; FN: number; TP: number }[];
  group_aware: { Model: string; "Target data added": string; "F1, random split": string; "F1, group-aware split": string }[];
}

/** One message through a saved model from the cross-domain study; nothing is stored. */
export function crossDomainClassify(text: string, classifier: CdClassifier, version: CdVersion): Promise<CdClassification> {
  return apiRequest<CdClassification>("/public/cross-domain/classify", { method: "POST", body: { text, classifier, version }, auth: false });
}

export function getCrossDomainResults(): Promise<CdResults> {
  return apiRequest<CdResults>("/public/cross-domain/results", { auth: false });
}
