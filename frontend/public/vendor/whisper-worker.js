// On-device speech-to-text for the Voice Call tab.
// Runs Whisper (tiny, 8-bit) in the browser through transformers.js, so it
// works in every modern browser (including Firefox/Brave, where the Web
// Speech API is missing or blocked) and audio never leaves the device.
// transformers.js and the ONNX Runtime wasm are self-hosted next to this
// file; only the model weights are fetched (once, then cached) from the
// official Hugging Face repo.
import { pipeline, env } from "/vendor/transformers-3.8.1/transformers.min.js";

env.allowLocalModels = false;
env.useBrowserCache = true;
env.backends.onnx.wasm.wasmPaths = "/vendor/transformers-3.8.1/";

const MODEL = "Xenova/whisper-tiny";
let asrPromise = null;

function getAsr(onProgress) {
  if (!asrPromise) {
    asrPromise = pipeline("automatic-speech-recognition", MODEL, {
      dtype: "q8",
      device: "wasm",
      progress_callback: onProgress,
    }).catch((err) => {
      asrPromise = null; // allow a retry after a network failure
      throw err;
    });
  }
  return asrPromise;
}

self.onmessage = async (event) => {
  const { id, audio, language } = event.data;
  const post = (msg) => self.postMessage({ id, ...msg });
  try {
    const files = new Map();
    const asr = await getAsr((p) => {
      if (p.status === "progress" && p.total) {
        files.set(p.file, [p.loaded, p.total]);
        let loaded = 0, total = 0;
        for (const [l, t] of files.values()) { loaded += l; total += t; }
        post({ type: "progress", stage: "download", percent: Math.round((loaded / total) * 100) });
      }
    });
    post({ type: "progress", stage: "transcribe" });
    const options = { chunk_length_s: 30, stride_length_s: 5, return_timestamps: false };
    if (language === "hi") Object.assign(options, { language: "hindi", task: "translate" });
    else Object.assign(options, { language: "english", task: "transcribe" });
    const out = await asr(audio, options);
    const text = (Array.isArray(out) ? out.map((o) => o.text).join(" ") : out.text).trim();
    post({ type: "done", text });
  } catch (err) {
    post({ type: "error", message: String((err && err.message) || err) });
  }
};
