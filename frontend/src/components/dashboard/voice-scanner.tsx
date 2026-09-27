"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, Square, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Textarea } from "@/components/ui/textarea";

interface Recognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: { results: { length: number; [index: number]: { [index: number]: { transcript: string } } } }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}
function recognitionConstructor(): (new () => Recognition) | undefined {
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}
interface VoiceScannerProps {
  onSubmitTranscript: (transcript: string) => void;
  onSubmitAudioFile: (file: File) => void;
  isScanning?: boolean;
}
export function VoiceScanner({ onSubmitTranscript, onSubmitAudioFile, isScanning = false }: VoiceScannerProps) {
  const [supported, setSupported] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const recognition = useRef<Recognition | null>(null);
  const timeout = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    setSupported(Boolean(recognitionConstructor()) && window.isSecureContext);
    return () => {
      clearTimeout(timeout.current);
      if (recognition.current) {
        recognition.current.onresult = null;
        recognition.current.onerror = null;
        recognition.current.onend = null;
        recognition.current.abort();
      }
    };
  }, []);
  function stop() {
    clearTimeout(timeout.current);
    recognition.current?.stop();
    setRecording(false);
  }
  function start() {
    const Ctor = recognitionConstructor();
    if (!Ctor || recording) return;
    setError(null);
    const instance = new Ctor();
    recognition.current = instance;
    instance.continuous = true;
    instance.interimResults = true;
    instance.lang = "en-IN";
    instance.onresult = event => {
      const parts: string[] = [];
      for (let i = 0; i < event.results.length; i++) parts.push(event.results[i]?.[0]?.transcript ?? "");
      setTranscript(parts.join(" ").slice(0, 4000));
    };
    instance.onerror = event => {
      const messages: Record<string, string> = {
        "not-allowed": "Microphone permission was denied. Allow access in your browser or paste a transcript below.",
        "service-not-allowed": "This browser does not allow speech recognition. Paste a transcript below.",
        "audio-capture": "No available microphone was found. Check your device connection and browser settings.",
        "no-speech": "No speech was detected. Try again or enter a transcript below.",
        network: "The browser speech service could not be reached. Try again or paste a transcript.",
      };
      clearTimeout(timeout.current);
      setRecording(false);
      if (event.error !== "aborted") setError(messages[event.error] ?? "Speech recognition stopped. Try again or paste a transcript.");
    };
    instance.onend = () => { clearTimeout(timeout.current); setRecording(false); };
    try {
      instance.start();
      setRecording(true);
      timeout.current = setTimeout(() => {
        instance.stop();
        setRecording(false);
        setError("Listening stopped after 60 seconds. Review your transcript or start another recording.");
      }, 60000);
    } catch {
      setRecording(false);
      setError("The microphone could not start. Check browser permissions and try again.");
    }
  }
  return <div className="space-y-5">
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-muted/20 p-5 sm:flex-row sm:items-center">
      <Button onClick={recording ? stop : start} disabled={!supported || isScanning} aria-label={recording ? "Stop listening" : "Start listening"}>
        {recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        {recording ? "Stop listening" : "Start listening"}
      </Button>
      <div className="min-w-0"><p className="text-sm font-medium" role="status">{recording ? "Listening · speak into your microphone" : supported ? "Browser speech recognition" : "Live transcription is unavailable in this browser"}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">Your browser may send audio to its speech service. Review the transcript before analysis.</p></div>
    </div>
    {error && <Alert variant="error">{error}</Alert>}
    <Textarea label="Voice transcript" value={transcript} onChange={e => setTranscript(e.target.value)} maxLength={4000} disabled={recording || isScanning} className="min-h-[160px]" placeholder="Speak using the microphone, or paste a call transcript here…" />
    <div className="flex items-center justify-between gap-3"><span className="text-xs text-muted-foreground">{transcript.length} / 4,000 characters</span><Button onClick={() => onSubmitTranscript(transcript.trim())} disabled={isScanning || recording || !transcript.trim()} isLoading={isScanning}>Analyze transcript</Button></div>
    <details className="rounded-lg border border-border p-5"><summary className="cursor-pointer text-sm font-medium">Upload a recorded call</summary>
      <p className="my-3 text-xs leading-5 text-muted-foreground">Audio uploads require an implemented server transcription provider. The standard project does not include one; an unavailable response will explain this. Pasted transcripts use the working analysis pipeline.</p>
      <label className="flex items-center gap-3 rounded-lg border border-dashed border-border p-4 text-sm"><Upload className="h-4 w-4" /><input aria-label="Audio evidence" type="file" accept="audio/*" disabled={isScanning || recording} className="min-w-0 w-full text-xs" onChange={e => {
        const candidate = e.target.files?.[0];
        setFile(null);
        if (candidate && (candidate.size > 8 * 1024 * 1024 || !candidate.type.startsWith("audio/"))) { setError("Choose an audio file smaller than 8 MB."); return; }
        setError(null); setFile(candidate ?? null);
      }} /></label>
      <Button className="mt-3" variant="outline" onClick={() => file && onSubmitAudioFile(file)} disabled={isScanning || recording || !file}>Analyze audio file</Button>
    </details>
  </div>;
}
