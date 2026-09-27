import { apiRequest } from "./client";

export interface ConfusionMatrix {
  true_positives: number;
  true_negatives: number;
  false_positives: number;
  false_negatives: number;
}

export interface ModelEvaluationEntry {
  model_name: string;
  version: string;
  is_production: boolean;
  trained_at: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  false_positive_rate: number;
  confusion_matrix: ConfusionMatrix;
  train_rows: number;
  test_rows: number;
  dataset_size: number;
  dataset_limitation_note: string | null;
}

export async function getModelEvaluations(): Promise<ModelEvaluationEntry[]> {
  return apiRequest<ModelEvaluationEntry[]>("/admin/model-evaluation", { method: "GET" });
}
