"""Extra measurements and figures for the paper (run after train_production.py).

    python -m ml_training.research.paper_extras

Writes extras.json and figures/*.pdf|png. Uses the registered production model (v4)
and the ThreatScorer exactly as the deployed service does.
"""

from __future__ import annotations

import json
import os
import random
import re
import time

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve  # noqa: E402

from ml_common.features.tfidf_vectorizer import TfidfConfig, TfidfFeatureExtractor  # noqa: E402
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline  # noqa: E402
from ml_common.registry.model_registry import ModelRegistry  # noqa: E402
from ml_service.inference.inference_engine import InferenceEngine  # noqa: E402
from ml_service.inference.threat_scorer import ThreatScorer  # noqa: E402
from ml_training.research.run_experiments import DS, Scores  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
ART = os.path.join(HERE, "..", "..", "artifacts")
plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 9, "axes.titlesize": 9, "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 300})
INK, ACC, ACC2, GREY = "#1f2a44", "#c0392b", "#2e86ab", "#9aa0a6"


def save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name + ".pdf"))
    fig.savefig(os.path.join(FIG, name + ".png"))
    plt.close(fig)


def obfuscate(t: str, rng: random.Random) -> str:
    """Tricks seen in real smishing: digit-for-letter swaps, spaced or dotted keywords, stray punctuation."""
    out = t
    for w in ("KYC", "kyc", "PAN", "OTP", "SIM", "blocked", "account", "update", "verify", "click", "suspended", "prize", "won"):
        if w in out and rng.random() < 0.8:
            style = rng.choice(["dots", "space", "leet"])
            if style == "dots":
                rep = ".".join(w)
            elif style == "space":
                rep = " ".join(w)
            else:
                rep = w.replace("o", "0").replace("O", "0").replace("i", "1").replace("e", "3").replace("a", "@")
            out = out.replace(w, rep, 1)
    return out


def main() -> int:
    df = pd.read_csv(DS)
    test = df[df.split == "test"].copy()
    train = df[df.split.isin(["train", "dev"])]
    y = (test.label == "scam").astype(int).values
    E = {}

    eng = InferenceEngine(ModelRegistry(root_dir=ART), TextPreprocessingPipeline(), "logistic_regression")
    eng.load()
    sc = ThreatScorer()
    t0 = time.perf_counter()
    p = np.array([eng.predict(t).scam_probability for t in test.text])
    t1 = time.perf_counter()
    f = np.array([sc.assess(float(q), eng.transform(t)[0], t).threat_score for t, q in zip(test.text, p)])
    t2 = time.perf_counter()
    test["p"], test["f"] = p, f
    info = eng.version_info
    E["model"] = {"name": info.model_name, "version": info.version, "train_rows": info.train_rows,
                  "model_bytes": os.path.getsize(os.path.join(ART, "logistic_regression", "v4", "model.joblib")),
                  "vectorizer_bytes": os.path.getsize(os.path.join(ART, "logistic_regression", "v4", "vectorizer.joblib")),
                  "features": len(eng.feature_names)}
    E["latency_ms_per_message"] = {"classifier": 1000 * (t1 - t0) / len(test), "classifier_plus_fusion": 1000 * ((t1 - t0) + (t2 - t1)) / len(test)}

    # training time of the production configuration (same settings as train_production.py)
    pre = TextPreprocessingPipeline()
    s0 = time.perf_counter()
    vec = TfidfFeatureExtractor(TfidfConfig(max_features=30000, min_df=2, char_ngram_range=(2, 5), char_max_features=60000))
    X = vec.fit_transform(pre.process_batch(train.text.astype(str).tolist()))
    LogisticRegression(C=16.0, max_iter=5000, class_weight="balanced").fit(X, (train.label == "scam").astype(int))
    E["training_seconds"] = time.perf_counter() - s0

    for name, s in (("classifier", p), ("final", f)):
        m = Scores(y, s).metrics(boot=1000)
        m["pr_auc"] = float(average_precision_score(y, s))
        E[f"real_test_{name}"] = m

    # threshold trade-off on the final score
    E["thresholds"] = []
    for thr in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        m = Scores(y, f).metrics(thr=thr, boot=0)
        E["thresholds"].append({"threshold": thr, "precision": m["precision"], "recall": m["recall"], "f1": m["f1"], "fpr": m["fpr"]})

    # error breakdown
    test["pred"] = (test.f >= 0.5).astype(int)
    g = test[test.label == "legitimate"]
    E["false_alarms_by_source"] = {k: {"n": int(len(v)), "flagged": int(v.pred.sum())} for k, v in g.groupby(g.subtype.where(g.source == "imc25", g.source + ":" + g.subtype))}
    s_ = test[test.label == "scam"]
    E["recall_by_scam_type"] = {k: {"n": int(len(v)), "caught": int(v.pred.sum())} for k, v in s_.groupby("subtype") if len(v) >= 10}

    # campaign structure
    sizes = df[df.is_synthetic == 0].groupby("campaign").size()
    imc_sizes = df[df.source == "imc25"].groupby("campaign").size()
    E["campaigns"] = {"real_campaigns": int(len(sizes)), "singletons": int((sizes == 1).sum()), "max_size": int(sizes.max()),
                      "rows_in_top_1pct": int(sizes.sort_values(ascending=False).head(max(1, len(sizes) // 100)).sum()), "real_rows": int(sizes.sum()),
                      "imc_campaigns": int(len(imc_sizes))}

    # robustness to obfuscation: word-only vs word+char features, same data and model
    rng = random.Random(7)
    sc_test = test[test.label == "scam"]
    obf = [obfuscate(t, rng) for t in sc_test.text]
    changed = np.array([o != t for o, t in zip(obf, sc_test.text)])
    E["robustness"] = {"scam_messages_changed": int(changed.sum())}
    ytr = (train.label == "scam").astype(int)
    for name, cfg in (("word", TfidfConfig(max_features=30000, min_df=2)), ("word+char", TfidfConfig(max_features=30000, min_df=2, char_ngram_range=(2, 5), char_max_features=60000))):
        v = TfidfFeatureExtractor(cfg)
        Xtr = v.fit_transform(pre.process_batch(train.text.astype(str).tolist()))
        m = LogisticRegression(C=16.0, max_iter=5000, class_weight="balanced").fit(Xtr, ytr)
        clean = m.predict_proba(v.transform(pre.process_batch([t for t, c in zip(sc_test.text, changed) if c])))[:, 1]
        dirty = m.predict_proba(v.transform(pre.process_batch([o for o, c in zip(obf, changed) if c])))[:, 1]
        E["robustness"][name] = {"recall_clean": float((clean >= 0.5).mean()), "recall_obfuscated": float((dirty >= 0.5).mean())}

    with open(os.path.join(HERE, "extras.json"), "w") as fh:
        json.dump(E, fh, indent=1)

    # ---------------- figures
    R = json.load(open(os.path.join(HERE, "results.json")))

    fig, ax = plt.subplots(1, 2, figsize=(6.8, 2.5))
    for s, lab, col in ((p, "classifier", ACC2), (f, "final verdict", ACC)):
        fpr, tpr, _ = roc_curve(y, s)
        ax[0].plot(fpr, tpr, color=col, lw=1.4, label=f"{lab} (AUC {roc_auc_score(y, s):.3f})")
        pr, rc, _ = precision_recall_curve(y, s)
        ax[1].plot(rc, pr, color=col, lw=1.4, label=f"{lab} (AP {average_precision_score(y, s):.3f})")
    ax[0].plot([0, 1], [0, 1], ls=":", color=GREY, lw=1)
    ax[0].set(xlabel="False-alarm rate", ylabel="Recall")
    ax[1].set(xlabel="Recall", ylabel="Precision", ylim=(0.6, 1.01))
    for a in ax:
        a.legend(frameon=False, loc="lower right")
    save(fig, "roc_pr")

    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    th = E["thresholds"]
    ax.plot([t["threshold"] for t in th], [100 * t["recall"] for t in th], marker="o", ms=3, color=ACC, label="recall (scams caught)")
    ax.plot([t["threshold"] for t in th], [100 * t["fpr"] for t in th], marker="s", ms=3, color=ACC2, label="false-alarm rate")
    ax.axvline(0.5, ls=":", color=GREY, lw=1)
    ax.set(xlabel="Decision threshold on final score", ylabel="%")
    ax.legend(frameon=False)
    save(fig, "threshold")

    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    a = R["E4_label_audit"]
    vals = [100 * a["reported_equals_scam"]["real_test"]["fpr"], 100 * a["audited"]["real_test"]["fpr"]]
    ax.bar(["reports taken\nas scam", "audited\nlabels"], vals, color=[GREY, ACC2], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.8, f"{v:.1f}%", ha="center", fontsize=8)
    ax.set(ylabel="False-alarm rate on real test (%)")
    save(fig, "label_audit")

    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    s_sorted = np.sort(sizes.values)[::-1]
    ax.loglog(np.arange(1, len(s_sorted) + 1), s_sorted, color=INK, lw=1.2)
    ax.set(xlabel="Campaign rank", ylabel="Messages in campaign")
    save(fig, "campaigns")

    fig, ax = plt.subplots(figsize=(3.3, 2.7))
    e6, e5 = R["E6_legacy_v3"]["real_test"]["fused"], R["E5_fusion"]["real_test"]["hand_fusion_v3"]
    labels = ["Accuracy", "F1", "False alarms"]
    old = [100 * e6["accuracy"], 100 * e6["f1"], 100 * e6["fpr"]]
    new = [100 * e5["accuracy"], 100 * e5["f1"], 100 * e5["fpr"]]
    x = np.arange(3)
    ax.bar(x - 0.18, old, 0.36, color=GREY, label="v3 (UCI 2011)")
    ax.bar(x + 0.18, new, 0.36, color=ACC, label="v4 (ScamGuard-IN-2026)")
    for i in range(3):
        ax.text(i - 0.18, old[i] + 1, f"{old[i]:.1f}", ha="center", fontsize=7)
        ax.text(i + 0.18, new[i] + 1, f"{new[i]:.1f}", ha="center", fontsize=7)
    ax.set_xticks(x, labels)
    ax.set(ylabel="%", ylim=(0, 110))
    ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.14))
    save(fig, "old_vs_new")

    tp, fp_, fn, tn = (int(((f >= .5) & (y == 1)).sum()), int(((f >= .5) & (y == 0)).sum()), int(((f < .5) & (y == 1)).sum()), int(((f < .5) & (y == 0)).sum()))
    with plt.rc_context({"font.size": 7, "legend.fontsize": 6.5}):
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(3.5, 1.75), gridspec_kw={"width_ratios": [1, 1.25]})
        M = np.array([[tn, fp_], [fn, tp]])
        a1.imshow(M, cmap="Blues")
        for i in range(2):
            for j in range(2):
                a1.text(j, i, str(M[i, j]), ha="center", va="center", color="white" if M[i, j] > M.max() / 2 else INK, fontsize=8)
        a1.set_xticks([0, 1], ["genuine", "scam"])
        a1.set_yticks([0, 1], ["genuine", "scam"])
        a1.set(xlabel="Predicted", ylabel="Actual")
        a1.set_title("(a) confusion matrix", fontsize=7)
        a2.plot([t["threshold"] for t in th], [100 * t["recall"] for t in th], marker="o", ms=2.5, color=ACC, label="recall")
        a2.plot([t["threshold"] for t in th], [100 * t["fpr"] for t in th], marker="s", ms=2.5, color=ACC2, label="false alarms")
        a2.axvline(0.5, ls=":", color=GREY, lw=1)
        a2.set(xlabel="Threshold", ylabel="%")
        a2.set_title("(b) threshold trade-off", fontsize=7)
        a2.legend(frameon=False, loc="center right")
        save(fig, "confusion")
    print(json.dumps({k: v for k, v in E.items() if k not in ("thresholds",)}, indent=1)[:3500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
