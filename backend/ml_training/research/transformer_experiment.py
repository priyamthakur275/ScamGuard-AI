"""ScamGuard v2: multilingual transformers vs the TF-IDF + LR system.

Run on a GPU (Google Colab T4 is enough, about 25-40 minutes for two models):

    python -m ml_training.research.transformer_experiment --models muril xlmr

CPU check of the whole pipeline with a tiny untrained model (no download, ~2 min):

    python -m ml_training.research.transformer_experiment --smoke

Protocol (same data and preprocessing as v2_experiments, so numbers compare directly):
  * train = ScamGuard-IN-2026 train split + synthetic Hinglish train rows; the dev split
    plus the Hinglish dev templates pick the best epoch; test sets are never used to choose
  * every message goes through ``deobfuscate`` first, as in v2
  * reported for each transformer: classifier alone, transformer + v2 risk engine (fusion),
    and a two-stage system (LR v2 decides; only messages in its 0.3-0.7 review band go
    to the transformer) - the realistic way to add a slow model to a fast service
  * McNemar test against LR v2 on every test set; per-message latency on the device used
  * T1 cross-domain: the same UCI -> India SMS protocol as research/cross_domain
    (A 80/20, B 70/30 stratified, seed 42): train on A, test on all of B and on B's 30%
    test part, then add 10% of B's pool. LR reference values come from that study.

Writes transformer_results.json and transformer_results.md next to this file
(``--out`` to change). Uploading those two files back to the repo is all that is needed.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time

import numpy as np
import pandas as pd

from ml_common.preprocessing.robust import deobfuscate
from ml_service.inference import threat_scorer as ts
from ml_training.datasets.scamguard_in_2026 import hinglish
from ml_training.research.run_experiments import DS, PRE, Scores, load_challenge, mcnemar
from ml_training.research.v2_experiments import ATTACKS, SEED, System

HERE = os.path.dirname(os.path.abspath(__file__))
CROSS = os.path.join(HERE, "..", "..", "..", "research", "cross_domain")
MODELS = {"muril": "google/muril-base-cased", "xlmr": "xlm-roberta-base", "mbert": "bert-base-multilingual-cased",
          "indicbert": "ai4bharat/IndicBERTv2-MLM-only", "distilmbert": "distilbert-base-multilingual-cased"}


def set_seed(s: int) -> None:
    import torch
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


def lab(d) -> np.ndarray:
    return (d.label == "scam").astype(int).values


# ------------------------------------------------------------------------------------------ model
class Transformer:
    def __init__(self, name: str, smoke: bool, train_texts: list[str], max_len: int):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch, self.max_len = torch, max_len
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if smoke:
            self.tok, self.model = self._tiny(train_texts)
        else:
            self.tok = AutoTokenizer.from_pretrained(MODELS.get(name, name))
            self.model = AutoModelForSequenceClassification.from_pretrained(MODELS.get(name, name), num_labels=2)
        self.model.to(self.device)

    @staticmethod
    def _tiny(texts):
        from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers
        from transformers import BertConfig, BertForSequenceClassification, PreTrainedTokenizerFast
        tk = Tokenizer(models.WordPiece(unk_token="[UNK]"))
        tk.normalizer = normalizers.BertNormalizer(lowercase=True)
        tk.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
        tk.train_from_iterator(texts, trainers.WordPieceTrainer(vocab_size=3000, special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]))
        from tokenizers.processors import TemplateProcessing
        tk.post_processor = TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", tk.token_to_id("[CLS]")), ("[SEP]", tk.token_to_id("[SEP]"))])
        tok = PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="[PAD]", unk_token="[UNK]", cls_token="[CLS]", sep_token="[SEP]", mask_token="[MASK]")
        cfg = BertConfig(vocab_size=tok.vocab_size, hidden_size=64, num_hidden_layers=2, num_attention_heads=2, intermediate_size=128, num_labels=2)
        return tok, BertForSequenceClassification(cfg)

    def _batches(self, texts, labels=None, bs=32, shuffle=False):
        idx = np.arange(len(texts))
        if shuffle:
            np.random.shuffle(idx)
        for i in range(0, len(idx), bs):
            j = idx[i:i + bs]
            enc = self.tok([texts[k] for k in j], truncation=True, max_length=self.max_len, padding=True, return_tensors="pt")
            enc = {k: v.to(self.device) for k, v in enc.items() if k in ("input_ids", "attention_mask", "token_type_ids")}
            yield enc, (self.torch.tensor(labels[j], device=self.device) if labels is not None else None)

    def fit(self, texts, y, dev_texts, dev_y, epochs=3, lr=2e-5, bs=32, log=print) -> list[dict]:
        torch = self.torch
        from transformers import get_linear_schedule_with_warmup
        opt = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=0.01)
        steps = epochs * ((len(texts) + bs - 1) // bs)
        sch = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
        w = torch.tensor([len(y) / (2 * max(1, (y == 0).sum())), len(y) / (2 * max(1, (y == 1).sum()))], dtype=torch.float, device=self.device)
        loss_fn = torch.nn.CrossEntropyLoss(weight=w)
        use_amp = self.device == "cuda"
        scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
        best, best_state, hist = -1.0, None, []
        for ep in range(epochs):
            self.model.train()
            t0, tot, n = time.time(), 0.0, 0
            for enc, yy in self._batches(texts, y, bs, shuffle=True):
                opt.zero_grad()
                with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                    loss = loss_fn(self.model(**enc).logits, yy)
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                scaler.step(opt); scaler.update(); sch.step()
                tot += float(loss) * len(yy); n += len(yy)
            p = self.predict(dev_texts)
            f1 = Scores(dev_y, p).metrics(boot=0)["f1"]
            hist.append({"epoch": ep + 1, "train_loss": tot / n, "dev_f1": f1, "seconds": round(time.time() - t0, 1)})
            log(f"  epoch {ep + 1}: loss {tot / n:.4f} dev F1 {f1:.4f} ({hist[-1]['seconds']} s)")
            if f1 > best:
                best = f1
                best_state = {k: v.detach().cpu().clone() for k, v in self.model.state_dict().items()}
        self.model.load_state_dict(best_state)
        return hist

    def predict(self, texts, bs=64) -> np.ndarray:
        torch = self.torch
        self.model.eval()
        out = []
        with torch.no_grad():
            for enc, _ in self._batches(list(texts), None, bs):
                with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=self.device == "cuda"):
                    out.append(torch.softmax(self.model(**enc).logits.float(), -1)[:, 1].cpu().numpy())
        return np.concatenate(out) if out else np.zeros(0)


def fuse(texts, probs) -> np.ndarray:
    sc = ts.ThreatScorer()
    return np.array([sc.assess(float(p), PRE.process_to_tokens(t), t).threat_score for t, p in zip(texts, probs)])


def brief(m: dict) -> dict:
    return {k: m[k] for k in ("n", "f1", "precision", "recall", "fpr", "roc_auc", "f1_ci", "fpr_ci") if k in m}


# ------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["muril", "xlmr"])
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max-len", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--smoke", action="store_true", help="tiny untrained model, small data, CPU: checks the pipeline only")
    ap.add_argument("--skip-cross-domain", action="store_true")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args(argv)
    boot = 100 if a.smoke else 1000
    import torch

    df = pd.read_csv(DS)
    train = pd.concat([df[df.split == "train"], pd.DataFrame(hinglish.train_rows())], ignore_index=True)
    dev = pd.concat([df[df.split == "dev"], pd.DataFrame(hinglish.dev_rows())], ignore_index=True)
    tests = {"real_test": df[df.split == "test"], "challenge": load_challenge(), "test_2026": df[df.split == "test_2026"],
             "hinglish_a_dev_check": pd.DataFrame(hinglish.test_rows()), "hinglish_b_final": pd.DataFrame(hinglish.test_b_rows())}
    r = random.Random(SEED)
    tests["real_test_attacked"] = tests["real_test"].assign(text=[ATTACKS["combined"](t, r) for t in tests["real_test"].text.astype(str)])
    if a.smoke:
        train = train.sample(600, random_state=1)
        dev = dev.sample(200, random_state=1)
        tests = {k: v.sample(min(len(v), 150), random_state=1) for k, v in tests.items()}
        a.models, a.epochs = ["tiny-untrained-bert"], 1

    R = {"protocol": {"train_rows": int(len(train)), "dev_rows": int(len(dev)), "epochs": a.epochs, "lr": a.lr, "batch": a.batch, "max_len": a.max_len,
                      "seed": a.seed, "smoke": a.smoke, "device": "cuda:" + torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
                      "torch": torch.__version__}, "models": {}}

    # LR v2 reference on the same train split (train only; dev is for model selection here)
    print("LR v2 reference ...", flush=True)
    lr_sys = System(train, robust=True)
    lr_scores = {k: lr_sys.score(d.text) for k, d in tests.items()}
    R["lr_v2"] = {k: {"classifier": brief(Scores(lab(tests[k]), v[0]).metrics(boot=boot)), "final": brief(Scores(lab(tests[k]), v[1]).metrics(boot=boot))} for k, v in lr_scores.items()}

    D = lambda texts: [deobfuscate(str(t)) for t in texts]
    for name in a.models:
        print(f"== {name}", flush=True)
        set_seed(a.seed)
        m = Transformer(name, a.smoke, D(train.text), a.max_len)
        hist = m.fit(D(train.text), lab(train), D(dev.text), lab(dev), a.epochs, a.lr, a.batch)
        res = {"history": hist, "tests": {}}
        for k, d in tests.items():
            y, texts = lab(d), D(d.text)
            t0 = time.perf_counter()
            p = m.predict(texts)
            ms = (time.perf_counter() - t0) * 1000 / max(1, len(texts))
            fused = fuse(texts, p)
            lr_final = lr_scores[k][1]
            band = (lr_final >= 0.3) & (lr_final < 0.7)
            two = np.where(band, fused, lr_final)
            res["tests"][k] = {"classifier": brief(Scores(y, p).metrics(boot=boot)), "fused": brief(Scores(y, fused).metrics(boot=boot)),
                               "two_stage": brief(Scores(y, two).metrics(boot=boot)), "two_stage_share_sent_to_transformer": float(band.mean()),
                               "mcnemar_fused_vs_lr_v2": mcnemar(y, lr_final, fused), "mcnemar_two_stage_vs_lr_v2": mcnemar(y, lr_final, two),
                               "ms_per_message": ms}
            print(f"  {k:22s} clf F1 {res['tests'][k]['classifier']['f1']:.4f} | fused F1 {res['tests'][k]['fused']['f1']:.4f} FPR {res['tests'][k]['fused']['fpr']:.4f} "
                  f"| two-stage F1 {res['tests'][k]['two_stage']['f1']:.4f} | LR v2 F1 {R['lr_v2'][k]['final']['f1']:.4f}", flush=True)
        R["models"][name] = res
        del m
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not a.skip_cross_domain:
        R["T1_cross_domain"] = cross_domain(a, D)

    os.makedirs(a.out, exist_ok=True)
    stem = "transformer_results_smoke" if a.smoke else "transformer_results"
    with open(os.path.join(a.out, stem + ".json"), "w") as fh:
        json.dump(R, fh, indent=1)
    write_md(R, os.path.join(a.out, stem + ".md"))
    print("wrote", os.path.join(a.out, stem + ".json"))
    return 0


def cross_domain(a, D) -> dict:
    from sklearn.model_selection import train_test_split
    A = pd.read_csv(os.path.join(CROSS, "data", "clean", "dataset_A_uci_clean.csv"))
    B = pd.read_csv(os.path.join(CROSS, "data", "clean", "dataset_B_india_clean.csv"))
    B = B[~B.message.isin(set(A.message))]
    a_tr, _ = train_test_split(A, test_size=0.20, stratify=A.label, random_state=42)
    pool, b_te = train_test_split(B, test_size=0.30, stratify=B.label, random_state=42)
    add10, _ = train_test_split(pool, train_size=0.10, stratify=pool.label, random_state=42)
    a_dev = a_tr.sample(frac=0.1, random_state=42)
    a_fit = a_tr.drop(a_dev.index)
    if a.smoke:
        a_fit, b_te, B = a_fit.sample(400, random_state=1), b_te.sample(150, random_state=1), B.sample(200, random_state=1)
    ref = json.load(open(os.path.join(CROSS, "outputs", "results.json")))
    lr_full_b = next(x["Target B F1"] for x in ref["cross_domain_full_B"] if x["Model"] == "Logistic Regression" and x["Feature"] == "word")
    adapt = {(x["target_fraction"]): x["B_f1_mean"] for x in ref["adaptation_summary"] if x["model"] == "logistic_regression" and x["feature"] == "word"}
    out = {"lr_reference": {"train_A_test_full_B": lr_full_b, "adapt_0pct_B_test_mean_3_seeds": adapt.get(0.0), "adapt_10pct_B_test_mean_3_seeds": adapt.get(0.1)}, "transformers": {}}
    for name in a.models:
        print(f"== cross-domain {name}", flush=True)
        row = {}
        for tag, tr in (("train_A", a_fit), ("train_A_plus_10pct_B", pd.concat([a_fit, add10]))):
            set_seed(a.seed)
            m = Transformer(name, a.smoke, D(tr.message), a.max_len)
            m.fit(D(tr.message), tr.label.astype(int).values, D(a_dev.message), a_dev.label.astype(int).values, a.epochs, a.lr, a.batch, log=lambda *_: None)
            row[tag] = {"B_test_f1": Scores(b_te.label.astype(int).values, m.predict(D(b_te.message))).metrics(boot=0)["f1"]}
            if tag == "train_A":
                row[tag]["full_B_f1"] = Scores(B.label.astype(int).values, m.predict(D(B.message))).metrics(boot=0)["f1"]
            print(f"  {tag}: {row[tag]}", flush=True)
            del m
        out["transformers"][name] = row
    return out


def write_md(R, path) -> None:
    f = lambda x: f"{100 * x:.1f}"
    L = ["# Transformer results", "", "Generated by `python -m ml_training.research.transformer_experiment`. Do not edit by hand.", "",
         f"Protocol: {json.dumps(R['protocol'])}", ""]
    if R["protocol"]["smoke"]:
        L += ["**SMOKE RUN: tiny untrained model on a small sample. These numbers only show the pipeline runs; they are not results.**", ""]
    for name, res in R["models"].items():
        L += [f"## {name}", "", "| Test set | LR v2 F1 / FPR | transformer F1 / FPR | transformer + risk engine F1 / FPR | two-stage F1 / FPR (share to transformer) | McNemar p (fused vs LR) | ms/msg |",
              "|---|---|---|---|---|---|---|"]
        for k, v in res["tests"].items():
            lr = R["lr_v2"][k]["final"]
            L.append(f"| {k} | {f(lr['f1'])} / {f(lr['fpr'])} | {f(v['classifier']['f1'])} / {f(v['classifier']['fpr'])} | {f(v['fused']['f1'])} / {f(v['fused']['fpr'])} | "
                     f"{f(v['two_stage']['f1'])} / {f(v['two_stage']['fpr'])} ({f(v['two_stage_share_sent_to_transformer'])}) | {v['mcnemar_fused_vs_lr_v2']['p_value']:.3g} | {v['ms_per_message']:.1f} |")
        L += ["", "Epochs: " + ", ".join(f"{h['epoch']}: dev F1 {f(h['dev_f1'])}" for h in res["history"]), ""]
    if "T1_cross_domain" in R:
        c = R["T1_cross_domain"]
        L += ["## T1. Cross-domain (UCI -> India SMS)", "", f"LR reference (research/cross_domain): train A, test full B F1 {f(c['lr_reference']['train_A_test_full_B'])}; "
              f"B test, 0% B {f(c['lr_reference']['adapt_0pct_B_test_mean_3_seeds'])}, 10% B {f(c['lr_reference']['adapt_10pct_B_test_mean_3_seeds'])} (mean of 3 seeds).", "",
              "| Model | train A: full B F1 | train A: B test F1 | + 10% B: B test F1 |", "|---|---|---|---|"]
        for n, row in c["transformers"].items():
            L.append(f"| {n} | {f(row['train_A']['full_B_f1'])} | {f(row['train_A']['B_test_f1'])} | {f(row['train_A_plus_10pct_B']['B_test_f1'])} |")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
