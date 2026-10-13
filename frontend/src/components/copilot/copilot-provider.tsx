"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { CopilotStreamError, streamCopilotChat } from "@/lib/copilot/stream";
import type { ChatMessage, ChatTurnPayload, CragVerdict } from "@/lib/copilot/types";

const STORAGE_KEY = "scamguard_copilot_chat_v1";
const MAX_STORED = 30;
const MAX_HISTORY_SENT = 12;

type Action =
  | { type: "hydrate"; messages: ChatMessage[] }
  | { type: "add"; message: ChatMessage }
  | { type: "append"; id: string; text: string }
  | { type: "verdict"; id: string; verdict: CragVerdict }
  | { type: "finish"; id: string }
  | { type: "fail"; id: string; error: string }
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

function isStoredMessage(value: unknown): value is ChatMessage {
  if (typeof value !== "object" || value === null) return false;
  const m = value as Record<string, unknown>;
  return typeof m.id === "string" && (m.role === "user" || m.role === "assistant") && typeof m.content === "string";
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
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          const restored = parsed.filter(isStoredMessage).map((m) => (m.status === "streaming" ? { ...m, status: "stopped" as const } : m));
          dispatch({ type: "hydrate", messages: restored });
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
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED)));
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
    try {
      await streamCopilotChat(
        text,
        history,
        (event) => {
          if (event.type === "token") dispatch({ type: "append", id: assistantId, text: event.text });
          else if (event.type === "verdict") dispatch({ type: "verdict", id: assistantId, verdict: event.verdict });
          else if (event.type === "error") dispatch({ type: "fail", id: assistantId, error: event.message });
          else if (event.type === "done") dispatch({ type: "finish", id: assistantId });
        },
        ac.signal,
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        dispatch({ type: "stop", id: assistantId });
      } else {
        const message = err instanceof CopilotStreamError ? err.message : "Something went wrong while answering.";
        dispatch({ type: "fail", id: assistantId, error: message });
      }
    } finally {
      if (controller.current === ac) controller.current = null;
    }
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
