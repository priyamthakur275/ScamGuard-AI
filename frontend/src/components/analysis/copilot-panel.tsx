"use client";

import { useState } from "react";
import { MessageCircleQuestion, Send } from "lucide-react";
import { askCopilot, type CopilotAnswer } from "@/lib/api/copilot";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface CopilotPanelProps {
  predictionId: string;
}

const QUICK_QUESTIONS = [
  "Why was this flagged?",
  "What evidence caused the risk?",
  "What is the attacker asking for?",
  "What should I do?",
  "Which indicators are suspicious?",
];

interface ConversationTurn {
  question: string;
  answer: CopilotAnswer;
}

/** Answers are grounded entirely in this scan's own real evidence (see
 * copilot_service.py) -- deterministic/template-based by default, since
 * no LLM provider is configured. The "source" badge tells you honestly
 * which path answered.
 */
export function CopilotPanel({ predictionId }: CopilotPanelProps) {
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(q: string) {
    if (!q.trim()) return;
    setIsAsking(true);
    setError(null);
    try {
      const answer = await askCopilot(predictionId, q);
      setTurns((prev) => [...prev, { question: q, answer }]);
      setQuestion("");
    } catch {
      setError("Couldn't get an answer. Please try again.");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="copilot-panel border border-border p-5 sm:p-6">
      <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <MessageCircleQuestion className="h-3.5 w-3.5 text-primary" />
        Copilot
      </p>
      <p className="mb-3 text-xs text-muted-foreground">Answers are grounded in this scan&apos;s saved evidence.</p>

      {QUICK_QUESTIONS.some((q) => !turns.some((t) => t.question === q)) && (
        <div className="mb-3 flex flex-wrap gap-2">
          {QUICK_QUESTIONS.filter((q) => !turns.some((t) => t.question === q)).map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              disabled={isAsking}
              className="rounded-md border border-border bg-card px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {turns.length > 0 && (
        <div className="mb-3 flex flex-col gap-3">
          {turns.map((turn, i) => (
            <div key={i} className="copilot-turn flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
              <p className="text-sm font-semibold text-foreground">{turn.question}</p>
              <p className="whitespace-pre-line text-sm leading-7 text-muted-foreground">{turn.answer.answer}</p>
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                Source: {turn.answer.source === "deterministic" ? "Evidence template (no LLM configured)" : "LLM"}
              </p>
            </div>
          ))}
        </div>
      )}

      {error && <p role="alert" className="mb-2 text-xs text-destructive">{error}</p>}

      <div className="flex gap-2 border-t border-border pt-4" aria-busy={isAsking}>
        <div className="min-w-0 flex-1">
        <Input
          aria-label="Ask Copilot a question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(question)}
          placeholder="Ask a question about this scan..."
          disabled={isAsking}
        />
        </div>
        <Button size="icon" isLoading={isAsking} onClick={() => ask(question)} disabled={isAsking || !question.trim()} aria-label="Ask">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
