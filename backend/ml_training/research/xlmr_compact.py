"""Can XLM-R run on a small CPU server? Fine-tune, shrink, quantise, measure.

    python -m ml_training.research.xlmr_compact --out /content/xlmr_compact          # GPU (Colab T4), ~6 min
    python -m ml_training.research.xlmr_compact --smoke --out /tmp/xc                 # CPU pipeline check, tiny model

Steps:
  1. Fine-tune XLM-R (or --model) on the v2 training split for 3 epochs, epoch chosen on dev, as in
     transformer_experiment.py, on de-obfuscated text.
  2. Vocabulary trimming: keep only the token ids that occur in the training text, plus special tokens.
     XLM-R's 250k-row embedding table holds most of its weights; unseen tokens map to <unk>.
     The kept ids come from training text only, never from a test set.
  3. Export to ONNX and quantise the weights to 8-bit integers (onnxruntime dynamic quantisation).
  4. Score the full model, the trimmed model and the quantised model on the real test set and the
     77 real Hindi messages, on CPU, and report size on disk, peak memory and latency.

Writes compact_results.json and compact_results.md, and (unless --no-save) the quantised model
(model.int8.onnx, vocab_map.npy, tokenizer files) under --out.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import time

import numpy as np
import pandas as pd

from ml_common.preprocessing.robust import deobfuscate
from ml_training.datasets.scamguard_in_2026 import hinglish
from ml_training.research.run_experiments import DS, Scores
from ml_training.research.transformer_experiment import MODELS, Transformer, lab, set_seed

HERE = os.path.dirname(os.path.abspath(__file__))


def rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1024 if os.uname().sysname == "Linux" else r / 1024 / 1024


def kept_ids(tok, texts, max_len) -> np.ndarray:
    ids = set(tok.all_special_ids)
    for i in range(0, len(texts), 512):
        for row in tok(texts[i:i + 512], truncation=True, max_length=max_len)["input_ids"]:
            ids.update(row)
    return np.array(sorted(ids), dtype=np.int64)


def trim(model, keep: np.ndarray):
    import torch
    old = model.get_input_embeddings()
    new = torch.nn.Embedding(len(keep), old.weight.shape[1], padding_idx=None)
    new.weight.data = old.weight.data[torch.as_tensor(keep)].clone()
    model.set_input_embeddings(new)
    model.config.vocab_size = len(keep)
    return model


def remap(keep: np.ndarray, vocab_size: int, unk_id: int) -> np.ndarray:
    m = np.full(vocab_size, int(np.searchsorted(keep, unk_id)), dtype=np.int64)
    m[keep] = np.arange(len(keep))
    return m


class OnnxScorer:
    def __init__(self, path, tok, vmap, max_len):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        self.s = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        self.tok, self.vmap, self.max_len = tok, vmap, max_len
        self.names = {i.name for i in self.s.get_inputs()}

    def predict(self, texts, bs=16):
        out = []
        for i in range(0, len(texts), bs):
            enc = self.tok(texts[i:i + bs], truncation=True, max_length=self.max_len, padding=True, return_tensors="np")
            feed = {"input_ids": self.vmap[enc["input_ids"]], "attention_mask": enc["attention_mask"].astype(np.int64)}
            if "token_type_ids" in self.names:
                feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
            logits = self.s.run(None, feed)[0]
            e = np.exp(logits - logits.max(1, keepdims=True))
            out.append(e[:, 1] / e.sum(1))
        return np.concatenate(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="xlmr")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--max-len", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "xlmr_compact"))
    a = ap.parse_args(argv)
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    os.makedirs(a.out, exist_ok=True)

    df = pd.read_csv(DS)
    train = pd.concat([df[df.split == "train"], pd.DataFrame(hinglish.train_rows())], ignore_index=True)
    dev = pd.concat([df[df.split == "dev"], pd.DataFrame(hinglish.dev_rows())], ignore_index=True)
    tests = {"real_test": df[df.split == "test"],
             "real_hindi": pd.read_csv(os.path.join(HERE, "..", "datasets", "scamguard_in_2026", "real_indic_test.csv"))}
    if a.smoke:
        train, dev = train.sample(400, random_state=1), dev.sample(100, random_state=1)
        tests = {k: v.sample(min(len(v), 60), random_state=1) for k, v in tests.items()}
        a.epochs = 1
    D = lambda s: [deobfuscate(str(t)) for t in s]
    trX, dvX = D(train.text), D(dev.text)

    set_seed(a.seed)
    m = Transformer(a.model, a.smoke, trX, a.max_len)
    hist = m.fit(trX, lab(train), dvX, lab(dev), a.epochs)
    tok, model = m.tok, m.model.float().cpu().eval()
    m.device = "cpu"

    R = {"model": MODELS.get(a.model, a.model), "seed": a.seed, "epochs": hist, "smoke": a.smoke, "variants": {}}
    full_params = sum(p.numel() for p in model.parameters())
    keep = kept_ids(tok, trX, a.max_len)
    vocab = model.get_input_embeddings().weight.shape[0]
    R["vocab"] = {"original": int(vocab), "kept": int(len(keep))}

    def evaluate(name, predict, size_mb=None):
        row = {"size_mb": size_mb}
        for k, d in tests.items():
            texts = D(d.text)
            t0 = time.perf_counter()
            p = predict(texts)
            ms = (time.perf_counter() - t0) * 1000 / len(texts)
            mm = Scores(lab(d), p).metrics(boot=0)
            row[k] = {"f1": mm["f1"], "fpr": mm["fpr"], "ms_per_message_cpu": ms}
        row["peak_rss_mb"] = rss_mb()
        R["variants"][name] = row
        print(name, json.dumps({k: (round(v["f1"], 4), round(v["fpr"], 4)) for k, v in row.items() if isinstance(v, dict)}), flush=True)
        return row

    torch.set_num_threads(1)
    evaluate("full_fp32_pytorch", m.predict, size_mb=full_params * 4 / 2**20)

    unk = tok.unk_token_id
    vmap = remap(keep, vocab, unk)
    model = trim(model, keep)
    m.model = model

    def trimmed_predict(texts, bs=16):
        out = []
        with torch.no_grad():
            for i in range(0, len(texts), bs):
                enc = tok(texts[i:i + bs], truncation=True, max_length=a.max_len, padding=True, return_tensors="pt")
                ids = torch.as_tensor(vmap[enc["input_ids"].numpy()])
                out.append(torch.softmax(model(input_ids=ids, attention_mask=enc["attention_mask"]).logits, -1)[:, 1].numpy())
        return np.concatenate(out)
    evaluate("trimmed_fp32_pytorch", trimmed_predict, size_mb=sum(p.numel() for p in model.parameters()) * 4 / 2**20)

    onnx_fp32 = os.path.join(a.out, "model.fp32.onnx")
    dummy = tok(["hello world"], return_tensors="pt")
    ids = torch.as_tensor(vmap[dummy["input_ids"].numpy()])
    torch.onnx.export(model, (ids, dummy["attention_mask"]), onnx_fp32, input_names=["input_ids", "attention_mask"], output_names=["logits"],
                      dynamic_axes={"input_ids": {0: "b", 1: "t"}, "attention_mask": {0: "b", 1: "t"}, "logits": {0: "b"}}, opset_version=17, dynamo=False)
    onnx_int8 = os.path.join(a.out, "model.int8.onnx")
    quantize_dynamic(onnx_fp32, onnx_int8, weight_type=QuantType.QInt8)
    os.remove(onnx_fp32)
    for f in os.listdir(a.out):
        if f.endswith(".data"):
            os.remove(os.path.join(a.out, f))
    sc = OnnxScorer(onnx_int8, tok, vmap, a.max_len)
    evaluate("trimmed_int8_onnx", sc.predict, size_mb=os.path.getsize(onnx_int8) / 2**20)

    if not a.no_save:
        np.save(os.path.join(a.out, "vocab_map.npy"), vmap)
        tok.save_pretrained(a.out)
    else:
        os.remove(onnx_int8)
    with open(os.path.join(a.out, "compact_results.json"), "w") as fh:
        json.dump(R, fh, indent=1)
    L = [f"# Compact {R['model']} (seed {a.seed}{', SMOKE: tiny untrained model' if a.smoke else ''})", "",
         f"Vocabulary {R['vocab']['original']:,} -> {R['vocab']['kept']:,} tokens kept (training text only).", "",
         "| Variant | size (MB) | real test F1 / FPR | real Hindi F1 / FPR | CPU ms/msg (1 thread) |", "|---|---|---|---|---|"]
    for n, v in R["variants"].items():
        L.append(f"| {n} | {v['size_mb']:.0f} | {100 * v['real_test']['f1']:.1f} / {100 * v['real_test']['fpr']:.1f} | "
                 f"{100 * v['real_hindi']['f1']:.1f} / {100 * v['real_hindi']['fpr']:.1f} | {v['real_test']['ms_per_message_cpu']:.1f} |")
    open(os.path.join(a.out, "compact_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
