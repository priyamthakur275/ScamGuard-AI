"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { CopilotStreamError, streamCopilotChat } from "@/lib/copilot/stream";
import { normalizeVerdict, type ChatMessage, type ChatTurnPayload, type CragVerdict } from "@/lib/copilot/types";

// localStorage keeps the chat across reloads and tabs. Pasted messages can be
// personal, so stored chats expire after a day and "Clear" removes them.
const STORAGE_KEY = "scamguard_copilot_chat_v2";
const LEGACY_KEYS = ["scamguard_copilot_chat_v1"];
const TTL_MS = 24 * 60 * 60 * 1000;
const MAX_STORED = 30;
const MAX_HISTORY_SENT = 12;
const AUTO_RETRIES = 2;

type Action =
  | { type: "hydrate"; messages: ChatMessage[] }
  | { type: "add"; message: ChatMessage }
  | { type: "append"; id: string; text: string }
  | { type: "verdict"; id: string; verdict: CragVerdict }
  | { type: "finish"; id: string }
  | { type: "fail"; id: string; error: string }
  | { type: "replace"; id: string; content: string }
  | { type: "stop"; id: string }
  | { type: "remove"; id: string }
  | { type: "clear" };

function reducer(state: ChatMessage[], action: Action): ChatMessage[] {
  switch (action.type) {
    case "hydrate":
      return action.messages;
    case "add":
      return [...state, action.message];
    case "append":
      return state.map((m) => (m.id === action.id ? { ...m, content: m.content + action.text } : m));
    case "verdict":
      return state.map((m) => (m.id === action.id ? { ...m, verdict: action.verdict } : m));
    case "finish":
      return state.map((m) => (m.id === action.id ? { ...m, status: "done" } : m));
    case "replace":
      return state.map((m) => (m.id === action.id ? { ...m, content: action.content, status: "done", error: undefined } : m));
    case "fail":
      return state.map((m) => (m.id === action.id ? { ...m, status: "error", error: action.error } : m));
    case "stop":
      return state.map((m) => (m.id === action.id ? { ...m, status: "stopped" } : m));
    case "remove":
      return state.filter((m) => m.id !== action.id);
    case "clear":
      return [];
  }
}

function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function restoreMessage(value: unknown): ChatMessage | null {
  if (typeof value !== "object" || value === null) return null;
  const m = value as Record<string, unknown>;
  if (typeof m.id !== "string" || (m.role !== "user" && m.role !== "assistant") || typeof m.content !== "string") return null;
  const status = m.status === "done" || m.status === "error" || m.status === "stopped" ? m.status : "stopped";
  const verdict = m.verdict === undefined ? undefined : normalizeVerdict(m.verdict) ?? undefined;
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    status,
    verdict,
    error: typeof m.error === "string" ? m.error : undefined,
    createdAt: typeof m.createdAt === "number" ? m.createdAt : Date.now(),
  };
}

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const id = window.setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      window.clearTimeout(id);
      reject(new DOMException("Aborted", "AbortError"));
    }, { once: true });
  });
}

interface CopilotContextValue {
  messages: ChatMessage[];
  busy: boolean;
  open: boolean;
  setOpen: (open: boolean) => void;
  send: (text: string) => Promise<void>;
  retry: (assistantId: string) => Promise<void>;
  stop: () => void;
  clear: () => void;
}

const CopilotContext = createContext<CopilotContextValue | undefined>(undefined);

export function CopilotProvider({ children }: { children: ReactNode }) {
  const [messages, dispatch] = useReducer(reducer, []);
  const [openState, setOpenState] = useReducer((_: boolean, next: boolean) => next, false);
  const controller = useRef<AbortController | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  messagesRef.current = messages;
  const hydrated = useRef(false);

  useEffect(() => {
    try {
      for (const key of LEGACY_KEYS) sessionStorage.removeItem(key);
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        const saved = typeof parsed === "object" && parsed !== null ? (parsed as { savedAt?: unknown; messages?: unknown }) : {};
        const fresh = typeof saved.savedAt === "number" && Date.now() - saved.savedAt < TTL_MS;
        if (fresh && Array.isArray(saved.messages)) {
          const restored = saved.messages.map(restoreMessage).filter((m): m is ChatMessage => m !== null);
          dispatch({ type: "hydrate", messages: restored });
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch {
      // Storage blocked (private mode) or corrupt: start with an empty chat.
    }
    hydrated.current = true;
  }, []);

  useEffect(() => {
    if (!hydrated.current) return;
    try {
      if (messages.length === 0) localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, JSON.stringify({ savedAt: Date.now(), messages: messages.slice(-MAX_STORED) }));
    } catch {
      // Storage full or blocked; the chat still works in memory.
    }
  }, [messages]);

  useEffect(() => () => controller.current?.abort(), []);

  const run = useCallback(async (text: string, history: ChatTurnPayload[]) => {
    controller.current?.abort();
    const ac = new AbortController();
    controller.current = ac;
    const assistantId = newId();
    dispatch({ type: "add", message: { id: assistantId, role: "assistant", content: "", status: "streaming", createdAt: Date.now() } });
    // Opening the stream retries with exponential backoff in the stream client.
    // A stream that opens but fails before the first word is retried here too;
    // once words have arrived, the user decides (Retry).
    for (let attempt = 0; ; attempt++) {
      const turn: { received: boolean; error: CopilotStreamError | null } = { received: false, error: null };
      try {
        await streamCopilotChat(
          text,
          history,
          (event) => {
            if (event.type === "token") {
              turn.received = true;
              dispatch({ type: "append", id: assistantId, text: event.text });
            } else if (event.type === "verdict") {
              turn.received = true;
              dispatch({ type: "verdict", id: assistantId, verdict: event.verdict });
            } else if (event.type === "error") {
              if (event.fallbackAnswer) dispatch({ type: "replace", id: assistantId, content: event.fallbackAnswer });
              else turn.error = new CopilotStreamError(event.message, event.retryable);
            } else if (event.type === "done") {
              dispatch({ type: "finish", id: assistantId });
            }
          },
          ac.signal,
        );
        if (!turn.error) break;
        throw turn.error;
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          dispatch({ type: "stop", id: assistantId });
          break;
        }
        // Connection failures were already retried with backoff inside the
        // stream client, so only failures after the stream opened retry here.
        const retryable = err instanceof CopilotStreamError ? err.retryable && err.phase === "stream" : false;
        if (retryable && !turn.received && attempt < AUTO_RETRIES) {
          try {
            await wait(1500 * 2 ** attempt, ac.signal);
          } catch {
            dispatch({ type: "stop", id: assistantId });
            break;
          }
          continue;
        }
        const message = err instanceof CopilotStreamError ? err.message : "Something went wrong while answering.";
        dispatch({ type: "fail", id: assistantId, error: message });
        break;
      }
    }
    if (controller.current === ac) controller.current = null;
  }, []);

  const historyBefore = useCallback((index: number): ChatTurnPayload[] => {
    return messagesRef.current
      .slice(0, index)
      .filter((m) => m.content.trim() && (m.role === "user" || m.status === "done"))
      .slice(-MAX_HISTORY_SENT)
      .map((m) => ({ role: m.role, content: m.content.slice(0, 4000) }));
  }, []);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim().slice(0, 4000);
      if (!text) return;
      const history = historyBefore(messagesRef.current.length);
      dispatch({ type: "add", message: { id: newId(), role: "user", content: text, status: "done", createdAt: Date.now() } });
      await run(text, history);
    },
    [historyBefore, run],
  );

  const retry = useCallback(
    async (assistantId: string) => {
      const list = messagesRef.current;
      const idx = list.findIndex((m) => m.id === assistantId);
      const userTurn = idx > 0 ? list[idx - 1] : undefined;
      if (!userTurn || userTurn.role !== "user") return;
      dispatch({ type: "remove", id: assistantId });
      await run(userTurn.content, historyBefore(idx - 1));
    },
    [historyBefore, run],
  );

  const stop = useCallback(() => controller.current?.abort(), []);
  const clear = useCallback(() => {
    controller.current?.abort();
    dispatch({ type: "clear" });
  }, []);

  const busy = messages.some((m) => m.status === "streaming");
  const value = useMemo<CopilotContextValue>(
    () => ({ messages, busy, open: openState, setOpen: setOpenState, send, retry, stop, clear }),
    [messages, busy, openState, send, retry, stop, clear],
  );

  return <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>;
}

export function useCopilot(): CopilotContextValue {
  const ctx = useContext(CopilotContext);
  if (!ctx) throw new Error("useCopilot must be used inside CopilotProvider");
  return ctx;
}
