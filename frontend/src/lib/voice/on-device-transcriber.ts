/** Thin client for public/vendor/whisper-worker.js (on-device Whisper). */

export type TranscribeLanguage = "en" | "hi";
export type TranscribeProgress = { stage: "decode" | "download" | "transcribe"; percent?: number };

const SAMPLE_RATE = 16000;
let worker: Worker | null = null;
let nextId = 0;

function getWorker(): Worker {
  if (!worker) worker = new Worker("/vendor/whisper-worker.js", { type: "module" });
  return worker;
}

/** Decode any browser-playable audio (webm/ogg/mp3/wav/m4a) to 16 kHz mono. */
export async function decodeToMono16k(blob: Blob): Promise<Float32Array> {
  const bytes = await blob.arrayBuffer();
  const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new Ctx();
  try {
    const decoded = await ctx.decodeAudioData(bytes.slice(0));
    const length = Math.ceil(decoded.duration * SAMPLE_RATE);
    const offline = new OfflineAudioContext(1, Math.max(length, 1), SAMPLE_RATE);
    const src = offline.createBufferSource();
    src.buffer = decoded;
    src.connect(offline.destination);
    src.start();
    const rendered = await offline.startRendering();
    return rendered.getChannelData(0);
  } finally {
    void ctx.close();
  }
}

export async function transcribeOnDevice(
  blob: Blob,
  language: TranscribeLanguage,
  onProgress: (p: TranscribeProgress) => void,
): Promise<string> {
  onProgress({ stage: "decode" });
  let audio: Float32Array;
  try {
    audio = await decodeToMono16k(blob);
  } catch {
    throw new Error("This audio format could not be decoded by your browser. Try an MP3, WAV, M4A or OGG file.");
  }
  if (audio.length < SAMPLE_RATE / 2) throw new Error("The recording is too short. Record at least a few words.");

  const id = ++nextId;
  const w = getWorker();
  return new Promise<string>((resolve, reject) => {
    const onMessage = (e: MessageEvent) => {
      const msg = e.data as { id: number; type: string; stage?: "download" | "transcribe"; percent?: number; text?: string; message?: string };
      if (msg.id !== id) return;
      if (msg.type === "progress" && msg.stage) onProgress({ stage: msg.stage, percent: msg.percent });
      else if (msg.type === "done") { cleanup(); resolve(msg.text ?? ""); }
      else if (msg.type === "error") {
        cleanup();
        reject(new Error(/fetch|network|Failed to load/i.test(msg.message ?? "")
          ? "Could not download the speech model. Check your internet connection and try again."
          : `On-device transcription failed: ${msg.message}`));
      }
    };
    const onError = () => { cleanup(); worker?.terminate(); worker = null; reject(new Error("The speech engine could not start in this browser.")); };
    function cleanup() { w.removeEventListener("message", onMessage); w.removeEventListener("error", onError); }
    w.addEventListener("message", onMessage);
    w.addEventListener("error", onError);
    const copy = new Float32Array(audio);
    w.postMessage({ id, audio: copy, language }, [copy.buffer]);
  });
}
