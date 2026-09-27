import { apiRequest } from "./client";

export interface CopilotAnswer {
  answer: string;
  grounded_in: string[];
  source: "deterministic" | "llm";
  intent: string;
}

export function askCopilot(predictionId: string, question: string): Promise<CopilotAnswer> {
  return apiRequest<CopilotAnswer>(`/messages/${predictionId}/copilot`, {
    method: "POST",
    body: { question },
  });
}
