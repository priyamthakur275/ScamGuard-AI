"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, BookOpen } from "lucide-react";

interface SimilarPatternsProps {
  patterns: Array<{ title: string; description: string }> | null | undefined;
  category?: string | null;
}

/** NOTE ON FRAMING: this content is a static, category-keyed reference
 * lookup (see PatternMatcher in explainable_ai.py) -- it describes common
 * tactics for the message's predicted category in general, not a
 * similarity match computed against THIS specific message's content. The
 * heading and intro line below are worded to reflect that honestly,
 * rather than implying a per-message pattern-matching capability that
 * doesn't exist.
 */
export function SimilarPatterns({ patterns, category }: SimilarPatternsProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!patterns || patterns.length === 0) return null;

  return (
    <div className="border border-border">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3 text-left font-mono text-xs uppercase tracking-wide text-foreground transition-colors hover:bg-muted"
        type="button"
      >
        <span className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
          {category ? `About ${category.replace(/_/g, " ")} scams` : "Background on this category"}
        </span>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {isOpen && (
        <div className="flex flex-col gap-3 border-t border-border px-4 py-3">
          <p className="text-xs text-muted-foreground">
            General tactics commonly seen in this scam category -- reference information, not a claim that this specific message was matched against a pattern database.
          </p>
          {patterns.map((pattern, i) => (
            <div key={i}>
              <p className="text-sm font-medium text-foreground">{pattern.title}</p>
              <p className="mt-0.5 text-sm text-muted-foreground">{pattern.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
