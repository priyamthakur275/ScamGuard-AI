"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, Square, Upload, Cpu, Radio, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  transcribeOnDevice,
  type TranscribeLanguage,
  type TranscribeProgress,
} from "@/lib/voice/on-device-transcriber";

/* ---------- Web Speech API typing (not in lib.dom for all TS versions) ---------- */
interface RecognitionResult { isFinal: boolean; [index: number]: { transcript: string } }
interface Recognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: { resultIndex: number; results: { length: number; [index: number]: RecognitionResult } }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}
function recognitionConstructor(): (new () => Recognition) | undefined {
  if (typeof window === "undefined") return undefined;
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}
/** Brave exposes webkitSpeechRecognition but always fails with "network". */
function isBrave(): boolean {
  return typeof navigator !== "undefined" && Boolean((navigator as unknown as { brave?: unknown }).brave);
}

type Mode = "live" | "device";
const MAX_SECONDS = 120;
const MAX_UPLOAD = 25 * 1024 * 1024;

interface VoiceScannerProps {
  onSubmitTranscript: (transcript: string) => void;
  isScanning?: boolean;
}

export function VoiceScanner({ onSubmitTranscript, isScanning = false }: VoiceScannerProps) {
  const [liveSupported, setLiveSupported] = useState(false);
  const [mode, setMode] = useState<Mode>("device");
  const [language, setLanguage] = useState<TranscribeLanguage>("en");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [progress, setProgress] = useState<TranscribeProgress | null>(null);

  const recognition = useRef<Recognition | null>(null);
  const wantLive = useRef(false);
  const baseText = useRef("");
  const liveText = useRef("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const ok = Boolean(recognitionConstructor()) && window.isSecureContext && !isBrave();
    setLiveSupported(ok);
    setMode(ok ? "live" : "device");
    return () => {
      clearInterval(timer.current);
      wantLive.current = false;
      if (recognition.current) {
        recognition.current.onresult = null;
        recognition.current.onerror = null;
        recognition.current.onend = null;
        recognition.current.abort();
      }
      recorder.current?.state === "recording" && recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const busy = isScanning || progress !== null;

  function startTimer(onLimit: () => void) {
    setSeconds(0);
    clearInterval(timer.current);
    timer.current = setInterval(() => {
      setSeconds((s) => {
        if (s + 1 >= MAX_SECONDS) {
          onLimit();
          return MAX_SECONDS;
        }
        return s + 1;
      });
    }, 1000);
  }

  function appendText(text: string) {
    const clean = text.trim();
    if (!clean) return;
    setTranscript((prev) => (prev.trim() ? `${prev.trim()} ${clean}` : clean).slice(0, 4000));
  }

  /* ---------------- Live mode: browser speech recognition ---------------- */
  function startLiveSession() {
    const Ctor = recognitionConstructor();
    if (!Ctor) return;
    const instance = new Ctor();
    recognition.current = instance;
    instance.continuous = true;
    instance.interimResults = true;
    instance.lang = "en-IN";
    instance.onresult = (event) => {
      let finals = "";
      let pending = "";
      for (let i = 0; i < event.results.length; i++) {
        const r = event.results[i];
        if (!r) continue;
        if (r.isFinal) finals += `${r[0]?.transcript ?? ""} `;
        else pending += r[0]?.transcript ?? "";
      }
      const joined = `${baseText.current} ${finals}`.replace(/\s+/g, " ").trim();
      liveText.current = joined.slice(0, 4000);
      setTranscript(liveText.current);
      setInterim(pending.trim());
    };
    instance.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "aborted") return; // onend restarts
      wantLive.current = false;
      stopTimerAndFlags();
      if (event.error === "network" || event.error === "service-not-allowed" || event.error === "language-not-supported") {
        setMode("device");
        setLiveSupported(false);
        setNotice("Your browser's speech service is unavailable, so ScamGuard switched to on-device transcription. Press Record again.");
        return;
      }
      const messages: Record<string, string> = {
        "not-allowed": "Microphone permission was denied. Click the lock icon in the address bar, allow the microphone, then try again.",
        "audio-capture": "No microphone was found. Check your device connection and browser settings.",
      };
      setError(messages[event.error] ?? "Speech recognition stopped unexpectedly. Try again or use on-device mode.");
    };
    instance.onend = () => {
      // Chrome ends sessions after silence or ~60 s; keep going while the user wants it.
      if (wantLive.current) {
        baseText.current = liveText.current;
        try {
          startLiveSession();
          return;
        } catch {
          /* fall through */
        }
      }
      stopTimerAndFlags();
    };
    instance.start();
  }

  function stopTimerAndFlags() {
    clearInterval(timer.current);
    setRecording(false);
    setInterim("");
  }

  function startLive() {
    setError(null);
    setNotice(null);
    baseText.current = transcript;
    liveText.current = transcript;
    wantLive.current = true;
    try {
      startLiveSession();
      setRecording(true);
      startTimer(stopLive);
    } catch {
      wantLive.current = false;
      setRecording(false);
      setError("The microphone could not start. Check browser permissions and try again.");
    }
  }

  function stopLive() {
    wantLive.current = false;
    recognition.current?.stop();
    stopTimerAndFlags();
  }

  /* ---------------- Device mode: record, then Whisper in the browser ---------------- */
  async function runTranscription(blob: Blob) {
    setError(null);
    setProgress({ stage: "decode" });
    try {
      const text = await transcribeOnDevice(blob, language, setProgress);
      if (!text) setError("No speech was recognised in that audio. Try speaking closer to the microphone.");
      else appendText(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transcription failed.");
    } finally {
      setProgress(null);
    }
  }

  async function startDevice() {
    setError(null);
    setNotice(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("This browser cannot record audio. Upload a recording or paste a transcript instead.");
      return;
    }
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      stream.current = s;
      const rec = new MediaRecorder(s);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
      rec.onstop = () => {
        s.getTracks().forEach((t) => t.stop());
        stream.current = null;
        clearInterval(timer.current);
        setRecording(false);
        if (chunks.length) void runTranscription(new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
      };
      recorder.current = rec;
      rec.start(1000);
      setRecording(true);
      startTimer(stopDevice);
    } catch (e) {
      const name = (e as { name?: string })?.name;
      setError(
        name === "NotAllowedError"
          ? "Microphone permission was denied. Click the lock icon in the address bar, allow the microphone, then try again."
          : name === "NotFoundError"
            ? "No microphone was found on this device."
            : "The microphone could not start. Check browser permissions and try again.",
      );
    }
  }

  function stopDevice() {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }

  const start = mode === "live" ? startLive : startDevice;
  const stop = mode === "live" ? stopLive : stopDevice;

  const progressLabel =
    progress?.stage === "download"
      ? `Downloading speech model (first time only, ~40 MB)${progress.percent != null ? ` · ${progress.percent}%` : ""}`
      : progress?.stage === "transcribe"
        ? "Transcribing on your device…"
        : progress
          ? "Preparing audio…"
          : null;

  const mmss = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

  return (
    <div className="space-y-5">
      {/* Engine + language */}
      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Transcription engine" className="inline-flex border border-border">
          {([
            ["live", "Live captions", Radio, !liveSupported],
            ["device", "On-device (Whisper)", Cpu, false],
          ] as const).map(([value, label, Icon, disabled]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={mode === value}
              disabled={disabled || recording || busy}
              onClick={() => setMode(value)}
              title={disabled ? "Not available in this browser" : undefined}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
                mode === value ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>
        {mode === "device" && (
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Call language
            <select
              aria-label="Call language"
              value={language}
              disabled={recording || busy}
              onChange={(e) => setLanguage(e.target.value as TranscribeLanguage)}
              className="border border-border bg-background px-2 py-1.5 text-xs text-foreground"
            >
              <option value="en">English</option>
              <option value="hi">Hindi / Hinglish → English</option>
            </select>
          </label>
        )}
      </div>

      {/* Record control */}
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-muted/20 p-5 sm:flex-row sm:items-center">
        <Button
          onClick={recording ? stop : start}
          disabled={busy}
          variant={recording ? "outline" : "primary"}
          aria-label={recording ? "Stop recording" : "Start recording"}
        >
          {recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          {recording ? "Stop" : "Record"}
        </Button>
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-sm font-medium" role="status" aria-live="polite">
            {recording && <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />}
            {recording
              ? `${mode === "live" ? "Listening" : "Recording"} · ${mmss} / 2:00`
              : progressLabel ?? (mode === "live" ? "Live captions as you speak" : "Record, then transcribe privately on this device")}
            {progress && <Loader2 className="h-4 w-4 animate-spin" />}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {mode === "live"
              ? "Uses your browser's speech service (Chrome, Edge, Safari). Put the call on speaker and hold the phone near the mic."
              : "Audio never leaves your device. Works in every modern browser, including Firefox and Brave."}
          </p>
        </div>
      </div>

      {notice && <Alert variant="info">{notice}</Alert>}
      {error && <Alert variant="error">{error}</Alert>}

      <div>
        <Textarea
          label="Voice transcript"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          maxLength={4000}
          disabled={recording || busy}
          className="min-h-[160px]"
          placeholder="Record the call, upload a recording, or paste a transcript here…"
        />
        {interim && <p className="mt-1 text-xs italic text-muted-foreground">…{interim}</p>}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">{transcript.length} / 4,000 characters</span>
        <div className="flex gap-2">
          {transcript && (
            <Button variant="ghost" onClick={() => setTranscript("")} disabled={recording || busy}>
              Clear
            </Button>
          )}
          <Button
            onClick={() => onSubmitTranscript(transcript.trim())}
            disabled={busy || recording || !transcript.trim()}
            isLoading={isScanning}
          >
            Analyze transcript
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-border p-5">
        <p className="text-sm font-medium">Upload a recorded call</p>
        <p className="my-2 text-xs leading-5 text-muted-foreground">
          MP3, WAV, M4A, OGG or WebM up to 25 MB. Transcribed on your device, then added to the transcript above.
        </p>
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-border p-4 text-sm">
          <Upload className="h-4 w-4" />
          <input
            aria-label="Audio evidence"
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.ogg,.webm,.aac"
            disabled={busy || recording}
            className="w-full min-w-0 text-xs"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (!f) return;
              if (f.size > MAX_UPLOAD) {
                setError("Choose an audio file smaller than 25 MB.");
                return;
              }
              void runTranscription(f);
            }}
          />
        </label>
      </div>
    </div>
  );
}
