"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Short name of the area, shown in the fallback and the log. */
  area?: string;
  /** Custom fallback; receives the error and a reset function. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** Render nothing on failure (for optional widgets such as the chat button). */
  silentFallback?: boolean;
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/** Catches render-time errors in its subtree so one broken widget cannot
 * blank the whole page. The error is logged with its component stack. */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[ScamGuard] ${this.props.area ?? "UI"} crashed:`, error, info.componentStack);
    this.props.onError?.(error, info);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (this.props.fallback) return this.props.fallback(error, this.reset);
    if (this.props.silentFallback) return null;
    return (
      <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm">
        <p className="flex items-center gap-2 font-medium text-destructive">
          <AlertTriangle className="h-4 w-4" />
          {this.props.area ? `${this.props.area} hit a problem.` : "This part of the page hit a problem."}
        </p>
        <p className="mt-1 text-muted-foreground">The rest of ScamGuard still works. You can try this part again.</p>
        <button
          type="button"
          onClick={this.reset}
          className="mt-3 inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs hover:border-primary"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Try again
        </button>
      </div>
    );
  }
}
