import { APP_API_URL, ApiError, apiRequest } from "@/lib/api/client";
import { normalizeVerdict, parseStreamEvent, type ChatTurnPayload, type CopilotAnalyzeResponse, type StreamEvent } from "./types";

export class CopilotStreamError extends Error {
  readonly retryable: boolean;
  readonly status?: number;
  /** "connect": the request could not be opened (already retried with backoff
   * here). "stream": it opened but failed or was cut off. */
  readonly phase: "connect" | "stream";

  constructor(message: string, retryable: boolean, status?: number, phase: "connect" | "stream" = "stream") {
    super(message);
    this.name = "CopilotStreamError";
    this.retryable = retryable;
    this.status = status;
    this.phase = phase;
  }
}

const CONNECT_TIMEOUT_MS = 125_000;
const IDLE_TIMEOUT_MS = 30_000;
const MAX_ATTEMPTS = 4;

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const id = window.setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort() {
      window.clearTimeout(id);
      reject(new DOMException("Aborted", "AbortError"));
    }
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

async function readError(response: Response): Promise<CopilotStreamError> {
  let message = "The assistant could not answer right now.";
  try {
    const body = (await response.json()) as { message?: string; details?: { msg?: string }[] };
    if (response.status === 422 && body.details?.[0]?.msg) {
      message = `That message can't be checked: ${body.details[0].msg.replace(/^Value error, /, "")}.`;
    } else if (body.message) {
      message = body.message;
    }
  } catch {
    // Non-JSON error page from a proxy; keep the generic message.
  }
  if (response.status === 429) message = "Too many messages in a short time. Please wait a few seconds and try again.";
  const retryable = response.status === 429 || response.status >= 500;
  return new CopilotStreamError(message, retryable, response.status, "connect");
}

/** Opens the SSE response, retrying with backoff while the server is waking up
 * or busy (network error, 429, 5xx). Retries stop once the stream has started. */
async function openStream(body: string, signal: AbortSignal): Promise<Response> {
  let lastError: CopilotStreamError = new CopilotStreamError("Could not reach ScamGuard.", true, undefined, "connect");
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    if (attempt > 0) await wait(Math.min(1500 * 2 ** (attempt - 1), 8000), signal);
    const timeout = new AbortController();
    const timer = window.setTimeout(() => timeout.abort(), CONNECT_TIMEOUT_MS);
    const onAbort = () => timeout.abort();
    signal.addEventListener("abort", onAbort, { once: true });
    try {
      const response = await fetch(`${APP_API_URL}/copilot/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body,
        signal: timeout.signal,
      });
      if (response.ok && response.body) return response;
      lastError = await readError(response);
      if (!lastError.retryable) throw lastError;
    } catch (err) {
      if (signal.aborted) throw new DOMException("Aborted", "AbortError");
      if (err instanceof CopilotStreamError && !err.retryable) throw err;
      if (!(err instanceof CopilotStreamError)) {
        lastError = new CopilotStreamError("Could not reach ScamGuard. Check your connection; the free server may be waking up.", true, undefined, "connect");
      }
    } finally {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", onAbort);
    }
  }
  throw lastError;
}

/** Streams one chat turn, calling onEvent for each server-sent event in order. */
export async function streamCopilotChat(
  message: string,
  history: ChatTurnPayload[],
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await openStream(JSON.stringify({ message, history }), signal);
  const reader = response.body!.getReader();
  // The connect-phase abort link is released once the response arrives, so
  // Stop must cancel the body reader directly to end the stream at once.
  const onAbort = () => void reader.cancel("stopped by user").catch(() => undefined);
  signal.addEventListener("abort", onAbort, { once: true });
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  let idleTimer = 0;
  const armIdle = () => {
    window.clearTimeout(idleTimer);
    idleTimer = window.setTimeout(() => void reader.cancel("idle timeout"), IDLE_TIMEOUT_MS);
  };

  const dispatch = (block: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (!data.length) return;
    const parsed = parseStreamEvent(event, data.join("\n"));
    if (!parsed) return;
    if (parsed.type === "done" || parsed.type === "error") finished = true;
    onEvent(parsed);
  };

  try {
    armIdle();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      armIdle();
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let sep = buffer.indexOf("\n\n");
      while (sep !== -1) {
        dispatch(buffer.slice(0, sep));
        buffer = buffer.slice(sep + 2);
        sep = buffer.indexOf("\n\n");
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) dispatch(buffer);
  } catch (err) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    throw new CopilotStreamError("The connection dropped while the answer was streaming.", true);
  } finally {
    window.clearTimeout(idleTimer);
    signal.removeEventListener("abort", onAbort);
  }
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  if (!finished) throw new CopilotStreamError("The answer was cut off before it finished.", true);
}

export async function analyzeWithCopilot(text: string): Promise<CopilotAnalyzeResponse> {
  let raw: unknown;
  try {
    raw = await apiRequest<unknown>("/copilot/analyze", { method: "POST", body: { text }, auth: false });
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new CopilotStreamError("Could not reach ScamGuard.", true);
  }
  const body = (typeof raw === "object" && raw !== null ? raw : {}) as Record<string, unknown>;
  const verdict = normalizeVerdict(body.verdict);
  const analysis = body.analysis as CopilotAnalyzeResponse["analysis"] | undefined;
  if (!verdict || !analysis || typeof analysis !== "object" || typeof analysis.verdict !== "string") {
    throw new CopilotStreamError("The server sent an answer in an unexpected format.", true);
  }
  return { verdict, analysis, answer: typeof body.answer === "string" ? body.answer : "" };
}
