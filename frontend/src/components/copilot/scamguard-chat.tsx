"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Mic, MicOff, RotateCcw, Send, Square, Trash2, Volume2, VolumeX, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/error-boundary";
import { useCopilot } from "./copilot-provider";
import { RagVerdict } from "./rag-verdict";
import type { ChatMessage } from "@/lib/copilot/types";

/** Shows **bold** from model answers as bold text (React escapes everything else). */
function renderInline(text: string) {
  return text.replace(/^#{1,4}\s+/gm, "").split(/(\*\*[^*\n]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4 ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  );
}

const STARTERS = [
  { label: "Bank KYC SMS", text: "Dear customer, your SBI YONO account will be blocked today. Update PAN at http://sbi-yono-kyc.xyz and share the OTP sent to your phone." },
  { label: "Call transcript", text: "Caller: This is Inspector Sharma from Mumbai Cyber Crime. A parcel with drugs was booked on your Aadhaar. You are under digital arrest, don't disconnect and don't tell your family." },
  { label: "Suspicious link", text: "http://paypa1-secure-login.verify-account.top/signin" },
];

const QUESTIONS = [
  "What is a digital arrest scam?",
  "I paid a scammer on UPI. What do I do now?",
  "How do I spot a fake customer care number?",
  "UPI collect request se paise kaise kat jaate hain?",
];

// ---- Voice: the browser's own speech APIs (free, nothing leaves the device
// except what the browser's speech service needs). Hidden where unsupported.
type Recognition = {
  lang: string; interimResults: boolean; continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null; onerror: (() => void) | null;
  start: () => void; stop: () => void;
};

function getRecognition(): (new () => Recognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const DEVANAGARI = /[\u0900-\u097F]/;

function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState(false);
  useEffect(() => setSupported(typeof window !== "undefined" && "speechSynthesis" in window), []);
  useEffect(() => () => { if (speaking) window.speechSynthesis.cancel(); }, [speaking]);
  if (!supported) return null;
  const toggle = () => {
    const synth = window.speechSynthesis;
    if (speaking) { synth.cancel(); setSpeaking(false); return; }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/\*\*/g, ""));
    u.lang = DEVANAGARI.test(text) ? "hi-IN" : "en-IN";
    u.rate = 0.95;
    u.onend = u.onerror = () => setSpeaking(false);
    synth.speak(u);
    setSpeaking(true);
  };
  return (
    <button type="button" onClick={toggle} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary" aria-label={speaking ? "Stop reading" : "Read aloud"}>
      {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />} {speaking ? "Stop" : "Listen"}
    </button>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2" aria-label="Analysing" role="status">
      <div className="flex items-center gap-3">
        <div className="h-16 w-16 animate-pulse rounded-full bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
        </div>
      </div>
      <div className="h-3 w-full animate-pulse rounded bg-muted" />
      <div className="h-3 w-5/6 animate-pulse rounded bg-muted" />
    </div>
  );
}

function AssistantBubble({ m, onRetry }: { m: ChatMessage; onRetry: () => void }) {
  const waiting = m.status === "streaming" && !m.content && !m.verdict;
  return (
    <div className="max-w-[92%] space-y-3 rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 text-sm">
      {waiting && <Skeleton />}
      {m.verdict && (
        <ErrorBoundary area="The verdict view">
          <RagVerdict verdict={m.verdict} compact />
        </ErrorBoundary>
      )}
      {m.content && (
        <p className="whitespace-pre-wrap leading-relaxed">
          {renderInline(m.content)}
          {m.status === "streaming" && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-primary align-middle" aria-hidden />}
        </p>
      )}
      {m.status === "done" && m.content && <SpeakButton text={m.content} />}
      {m.status === "stopped" && <p className="text-xs text-muted-foreground">Stopped.</p>}
      {m.status === "error" && (
        <div role="alert" className="flex flex-wrap items-center gap-2 text-xs text-destructive">
          <span>{m.error}</span>
          <button type="button" onClick={onRetry} className="inline-flex items-center gap-1 rounded-md border border-destructive/40 px-2 py-1 hover:bg-destructive/10">
            <RotateCcw className="h-3 w-3" /> Retry
          </button>
        </div>
      )}
    </div>
  );
}

function ChatPanel() {
  const { messages, busy, send, retry, stop, clear, setOpen } = useCopilot();
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recRef = useRef<Recognition | null>(null);
  const [listening, setListening] = useState(false);
  const [voiceLang, setVoiceLang] = useState<"en-IN" | "hi-IN">("en-IN");
  const [canListen, setCanListen] = useState(false);
  useEffect(() => setCanListen(getRecognition() !== null), []);
  useEffect(() => () => recRef.current?.stop(), []);

  const toggleMic = () => {
    if (listening) { recRef.current?.stop(); return; }
    const Rec = getRecognition();
    if (!Rec) return;
    const rec = new Rec();
    rec.lang = voiceLang;
    rec.interimResults = true;
    rec.continuous = false;
    const before = draft ? draft.trimEnd() + " " : "";
    rec.onresult = (e) => {
      const said = Array.from(e.results).map((r) => r[0]?.transcript ?? "").join("");
      setDraft((before + said).slice(0, 4000));
    };
    rec.onend = rec.onerror = () => { setListening(false); recRef.current = null; };
    recRef.current = rec;
    setListening(true);
    rec.start();
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  const submit = (text: string) => {
    if (!text.trim() || busy) return;
    setDraft("");
    void send(text);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit(draft);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(draft);
    }
  };

  return (
    <section
      role="dialog"
      aria-label="ScamGuard Copilot"
      className="fixed inset-0 z-50 flex max-h-none flex-col overflow-hidden rounded-none border-border bg-background p-0 shadow-2xl sm:inset-auto sm:rounded-2xl sm:bottom-24 sm:right-5 sm:h-[min(640px,calc(100vh-8rem))] sm:w-[420px] sm:rounded-2xl sm:border"
    >
      <header className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div>
          <p className="font-semibold">ScamGuard Copilot</p>
          <p className="text-xs text-muted-foreground">Check a message, or ask anything about staying safe</p>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button type="button" onClick={clear} className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Clear conversation">
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          <button type="button" onClick={() => setOpen(false)} className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {messages.length === 0 && (
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>Paste a suspicious message, link or call transcript and I&apos;ll check it against the trained model, the scam-intent engine and a library of known Indian scams. You can also ask me anything, by typing or with the mic, in English or Hindi.</p>
            <p className="text-xs font-medium uppercase tracking-wide">Check an example</p>
            <div className="flex flex-wrap gap-2">
              {STARTERS.map((s) => (
                <button key={s.label} type="button" onClick={() => submit(s.text)} className="rounded-full border border-border px-3 py-1 text-xs hover:border-primary hover:text-primary">
                  {s.label}
                </button>
              ))}
            </div>
            <p className="text-xs font-medium uppercase tracking-wide">Or ask</p>
            <div className="flex flex-col items-start gap-1.5">
              {QUESTIONS.map((q) => (
                <button key={q} type="button" onClick={() => submit(q)} className="rounded-xl border border-border px-3 py-1.5 text-left text-xs hover:border-primary hover:text-primary">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end">
              <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-tr-sm border border-primary/40 bg-primary/10 px-4 py-2.5 text-sm">{m.content}</p>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start">
              <AssistantBubble m={m} onRetry={() => void retry(m.id)} />
            </div>
          ),
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={onSubmit} className="border-t border-border p-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value.slice(0, 4000))}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="Paste a message to check, or ask me anything…"
            aria-label="Message for ScamGuard Copilot"
            className="max-h-40 min-h-[44px] flex-1 resize-y rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {canListen && (
            <div className="flex flex-col items-center gap-0.5">
              <button
                type="button"
                onClick={toggleMic}
                className={cn("inline-flex h-11 w-11 items-center justify-center rounded-xl border border-border hover:bg-muted", listening && "animate-pulse border-destructive text-destructive")}
                aria-label={listening ? "Stop listening" : "Speak your question"}
                aria-pressed={listening}
              >
                {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </button>
              <button type="button" onClick={() => setVoiceLang((l) => (l === "en-IN" ? "hi-IN" : "en-IN"))} disabled={listening}
                className="text-[10px] text-muted-foreground hover:text-primary" aria-label="Voice language">
                {voiceLang === "en-IN" ? "EN" : "हिं"}
              </button>
            </div>
          )}
          {busy ? (
            <button type="button" onClick={stop} className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-border hover:bg-muted" aria-label="Stop">
              <Square className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!draft.trim()}
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground disabled:opacity-40"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
        <p className="mt-1.5 text-[11px] text-muted-foreground">Not stored on our servers. This chat stays in this browser for 24 hours (bin icon clears it). Never paste your own OTP or PIN.</p>
      </form>
    </section>
  );
}

/** Floating launcher + chat panel. Wrapped in an error boundary so a failure
 * inside the chat can never take the page down with it. */
export function ScamGuardChat() {
  const { open, setOpen, busy } = useCopilot();
  return (
    <ErrorBoundary area="Copilot" silentFallback>
      <div className="print:hidden">
        {open && (
          <ErrorBoundary area="Copilot" fallback={(_e, reset) => (
            <div role="alert" className="fixed bottom-24 right-5 z-50 w-72 rounded-xl border border-destructive/40 bg-background p-4 text-sm shadow-xl">
              <p className="font-medium text-destructive">The Copilot hit a problem.</p>
              <button type="button" onClick={reset} className="mt-2 text-xs text-primary underline">Reload the chat</button>
            </div>
          )}>
            <ChatPanel />
          </ErrorBoundary>
        )}
        {!open && (
          <button type="button" onClick={() => setOpen(true)} className="fixed bottom-[5.5rem] right-5 z-50 hidden rounded-2xl rounded-br-sm border border-border bg-card px-3 py-2 text-xs font-medium text-foreground shadow-lg sm:block">
            Hi! How may I help you?
          </button>
        )}
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label={open ? "Close ScamGuard Copilot" : "Open ScamGuard Copilot"}
          className={cn(
            "fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-[999px] bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105",
            open && "hidden sm:flex",
          )}
        >
          {open ? <X className="h-6 w-6" /> : (
            <svg viewBox="0 0 32 32" className="h-9 w-9" aria-hidden="true">
              <line x1="16" y1="3" x2="16" y2="7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <circle cx="16" cy="3" r="1.8" fill="currentColor" />
              <rect x="6" y="7" width="20" height="16" rx="6" fill="currentColor" />
              <circle cx="12" cy="15" r="2.4" className="fill-primary motion-safe:animate-pulse" />
              <circle cx="20" cy="15" r="2.4" className="fill-primary motion-safe:animate-pulse" />
              <rect x="12" y="19" width="8" height="1.6" rx="0.8" className="fill-primary" />
              <rect x="3" y="12" width="3" height="6" rx="1.5" fill="currentColor" />
              <rect x="26" y="12" width="3" height="6" rx="1.5" fill="currentColor" />
              <rect x="11" y="24" width="10" height="5" rx="2" fill="currentColor" />
            </svg>
          )}
          {busy && !open && <span className="absolute right-1 top-1 h-2.5 w-2.5 animate-pulse rounded-[999px] bg-caution" aria-hidden />}
        </button>
      </div>
    </ErrorBoundary>
  );
}
