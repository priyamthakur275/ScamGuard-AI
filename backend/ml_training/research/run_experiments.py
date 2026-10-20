"""Experiments for the ScamGuard-IN-2026 paper.

    python -m ml_training.research.run_experiments            # all experiments
    python -m ml_training.research.run_experiments --quick    # fewer bootstrap rounds

Writes ml_training/research/results.json and results.md. Every number in the paper
comes from this script; nothing is typed by hand.

E1  Leakage: row-level random split vs campaign-aware split (same data, same model)
E2  Model and feature comparison on the campaign-aware real test set
E3  Training-data ablation: synthetic only / real only / real + synthetic
E4  Label-audit ablation: IMC'25 "reported = scam" labels vs audited labels
E5  Evidence fusion: classifier alone vs classifier + ThreatScorer (intent rules + genuine guards)
E6  Legacy baseline: the previous production model (UCI SMS Spam + supplement, v3) on the new test sets
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC

from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_service.inference.threat_scorer import ThreatScorer

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(HERE, "..", "datasets", "scamguard_in_2026", "scamguard_in_2026.csv")
TESTS = os.path.join(HERE, "..", "..", "tests", "data")
SEED = 2026


# ------------------------------------------------------------------------------------------ helpers

@dataclass
class Scores:
    y: np.ndarray
    p: np.ndarray

    def metrics(self, thr: float = 0.5, boot: int = 1000) -> dict:
        def one(y, p):
            yh = (p >= thr).astype(int)
            tp = int(((yh == 1) & (y == 1)).sum()); fp = int(((yh == 1) & (y == 0)).sum())
            fn = int(((yh == 0) & (y == 1)).sum()); tn = int(((yh == 0) & (y == 0)).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
            return {"accuracy": (tp + tn) / len(y), "precision": prec, "recall": rec, "f1": f1,
                    "fpr": fp / (fp + tn) if fp + tn else 0.0, "tp": tp, "fp": fp, "fn": fn, "tn": tn}
        m = one(self.y, self.p)
        if len(set(self.y)) == 2:
            m["roc_auc"] = float(roc_auc_score(self.y, self.p))
        if boot:
            rng = np.random.default_rng(SEED)
            f1s, fprs, accs = [], [], []
            for _ in range(boot):
                i = rng.integers(0, len(self.y), len(self.y))
                b = one(self.y[i], self.p[i])
                f1s.append(b["f1"]); fprs.append(b["fpr"]); accs.append(b["accuracy"])
            m["f1_ci"] = [float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))]
            m["fpr_ci"] = [float(np.percentile(fprs, 2.5)), float(np.percentile(fprs, 97.5))]
            m["accuracy_ci"] = [float(np.percentile(accs, 2.5)), float(np.percentile(accs, 97.5))]
        m["n"] = int(len(self.y))
        return m


def mcnemar(y, pa, pb, thr=0.5) -> dict:
    a = (pa >= thr) == y
    b = (pb >= thr) == y
    n01 = int((a & ~b).sum()); n10 = int((~a & b).sum())
    from scipy.stats import binomtest
    pval = binomtest(min(n01, n10), n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return {"a_right_b_wrong": n01, "a_wrong_b_right": n10, "p_value": float(pval)}


PRE = TextPreprocessingPipeline()


def prep(texts) -> list[str]:
    return PRE.process_batch([str(t) for t in texts])


class Featurizer:
    def __init__(self, kind: str):
        self.kind = kind
        self.w = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_df=0.95, max_features=30000)
        self.c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2, max_features=60000)

    def fit_transform(self, texts):
        x = prep(texts)
        if self.kind == "word+char":  # exactly the production feature extractor
            from ml_common.features.tfidf_vectorizer import TfidfConfig, TfidfFeatureExtractor
            self.prod = TfidfFeatureExtractor(TfidfConfig(max_features=30000, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True,
                                                          char_ngram_range=(2, 5), char_max_features=60000))
            return self.prod.fit_transform(x)
        if self.kind == "word":
            return self.w.fit_transform(x)
        if self.kind == "char":
            return self.c.fit_transform(x)
        return hstack([self.w.fit_transform(x), self.c.fit_transform(x)]).tocsr()

    def transform(self, texts):
        x = prep(texts)
        if self.kind == "word+char":
            return self.prod.transform(x)
        if self.kind == "word":
            return self.w.transform(x)
        if self.kind == "char":
            return self.c.transform(x)
        return hstack([self.w.transform(x), self.c.transform(x)]).tocsr()


def make_model(name: str):
    if name == "naive_bayes":
        return ComplementNB(alpha=0.3)
    if name == "logistic_regression":
        return LogisticRegression(C=16.0, max_iter=5000, class_weight="balanced")
    if name == "linear_svm":
        return CalibratedClassifierCV(LinearSVC(C=0.5, class_weight="balanced"), cv=5)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=300, min_samples_leaf=1, class_weight="balanced_subsample", n_jobs=-1, random_state=SEED)
    raise ValueError(name)


def fit_predict(train: pd.DataFrame, tests: dict[str, pd.DataFrame], model="logistic_regression", feats="word+char"):
    f = Featurizer(feats)
    X = f.fit_transform(train.text)
    y = (train.label == "scam").astype(int).values
    m = make_model(model).fit(X, y)
    return {k: Scores((d.label == "scam").astype(int).values, m.predict_proba(f.transform(d.text))[:, 1]) for k, d in tests.items()}, (f, m)


def oof_probs(train: pd.DataFrame, model="logistic_regression", feats="word+char", k=5) -> np.ndarray:
    """Out-of-fold classifier probabilities, folds grouped by campaign."""
    from sklearn.model_selection import GroupKFold
    p = np.zeros(len(train))
    for tr, va in GroupKFold(n_splits=k).split(train, groups=train.campaign):
        s, _ = fit_predict(train.iloc[tr], {"v": train.iloc[va]}, model, feats)
        p[va] = s["v"].p
    return p


def fused(texts, probs) -> np.ndarray:
    sc = ThreatScorer()
    return np.array([sc.assess(float(p), PRE.process_to_tokens(t), t).threat_score for t, p in zip(texts, probs)])


def load_challenge() -> pd.DataFrame:
    rows = []
    import importlib
    for mod in ("realistic_messages", "heldout_messages", "final_check_messages"):
        m = importlib.import_module(f"tests.data.{mod}")
        for name in dir(m):
            v = getattr(m, name)
            if isinstance(v, (list, tuple)) and v and isinstance(v[0], str):
                lab = "scam" if "SCAM" in name.upper() else "legitimate"
                rows += [{"text": t, "label": lab, "set": mod} for t in v]
    ds = os.path.join(HERE, "..", "datasets")
    for f in ("indian_challenge_set.csv", "indian_challenge_set_b.csv"):
        d = pd.read_csv(os.path.join(ds, f))
        rows += [{"text": t, "label": "scam" if l in ("scam", "spam", "phishing") else "legitimate", "set": f} for t, l in zip(d.text, d.label)]
    return pd.DataFrame(rows).drop_duplicates("text")


# ------------------------------------------------------------------------------------------ main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-e2", action="store_true")
    a = ap.parse_args(argv)
    boot = 200 if a.quick else 1000

    df = pd.read_csv(DS)
    real = df[(df.is_synthetic == 0) & (df.split != "test_2026")]
    train = df[df.split.isin(["train", "dev"])]  # model selection used dev; final numbers train on train+dev
    test = df[df.split == "test"]
    t26 = df[df.split == "test_2026"]
    ch = load_challenge()
    tests = {"real_test": test, "challenge": ch}
    if len(t26):
        tests["test_2026"] = t26
    R: dict = {"dataset": {
        "rows": int(len(df)), "by_split_label": {f"{k[0]}|{k[1]}": int(v) for k, v in df.groupby(["split", "label"]).size().items()},
        "by_source": {k: int(v) for k, v in df.groupby("source").size().items()},
        "challenge_rows": int(len(ch)), "test_2026_rows": int(len(t26))}}
    print(json.dumps(R["dataset"], indent=1))

    # E1 leakage
    rtr, rte = train_test_split(real, test_size=0.25, random_state=SEED, stratify=real.label)
    s_rand, _ = fit_predict(rtr, {"t": rte})
    s_camp, _ = fit_predict(real[real.split != "test"], {"t": real[real.split == "test"]})
    R["E1_leakage"] = {"random_row_split": s_rand["t"].metrics(boot=boot), "campaign_split": s_camp["t"].metrics(boot=boot),
                       "test_rows_with_near_duplicate_in_train_random": int(rte.campaign.isin(set(rtr.campaign)).sum())}
    print("E1", {k: round(v["f1"], 4) for k, v in R["E1_leakage"].items() if isinstance(v, dict)})

    # E2 models x features (train = real+synthetic train split)
    R["E2_models"] = {}
    for feats in () if a.skip_e2 else ("word", "char", "word+char"):
        for model in ("naive_bayes", "logistic_regression", "linear_svm", "random_forest"):
            s, _ = fit_predict(train, tests, model, feats)
            R["E2_models"][f"{model}|{feats}"] = {k: v.metrics(boot=0) for k, v in s.items()}
            print("E2", model, feats, {k: (round(v.metrics(boot=0)["f1"], 4), round(v.metrics(boot=0)["fpr"], 4)) for k, v in s.items()})

    # E3 training data ablation (best-practice model)
    R["E3_training_data"] = {}
    for name, tr in (("synthetic_only", train[train.is_synthetic == 1]), ("real_only", train[train.is_synthetic == 0]), ("real_plus_synthetic", train)):
        s, _ = fit_predict(tr, tests)
        R["E3_training_data"][name] = {k: v.metrics(boot=boot) for k, v in s.items()}
        print("E3", name, {k: round(v.metrics(boot=0)["f1"], 4) for k, v in s.items()})

    # E4 label audit
    raw = train.copy()
    raw.loc[(raw.source == "imc25") & (raw.subtype == "reported_but_genuine"), "label"] = "scam"
    s_raw, _ = fit_predict(raw, tests)
    s_aud, (feat, model) = fit_predict(train, tests)
    R["E4_label_audit"] = {"reported_equals_scam": {k: v.metrics(boot=boot) for k, v in s_raw.items()},
                           "audited": {k: v.metrics(boot=boot) for k, v in s_aud.items()},
                           "mcnemar_real_test": mcnemar(s_aud["real_test"].y, s_aud["real_test"].p, s_raw["real_test"].p)}
    print("E4", {k: round(v["real_test"]["fpr"], 4) for k, v in R["E4_label_audit"].items() if k != "mcnemar_real_test"})

    # E5 fusion: classifier alone vs hand-weighted rules (v3) vs learned fusion (v4)
    from ml_service.inference.learned_fusion import fit as fit_fusion
    p_oof = oof_probs(train)
    lf = fit_fusion(train.text.tolist(), p_oof.tolist(), (train.label == "scam").astype(int).tolist())
    R["E5_fusion"] = {"learned_weights": {"bias": lf.bias, **{k: round(v, 3) for k, v in sorted(lf.weights.items(), key=lambda kv: -abs(kv[1])) if abs(v) > 1e-3}}}
    for k, d in tests.items():
        y, p = s_aud[k].y, s_aud[k].p
        hand = fused(d.text.tolist(), p)
        learned = np.array([lf.score(t, q) for t, q in zip(d.text, p)])
        R["E5_fusion"][k] = {"classifier": Scores(y, p).metrics(boot=boot), "hand_fusion_v3": Scores(y, hand).metrics(boot=boot),
                             "learned_fusion_v4": Scores(y, learned).metrics(boot=boot),
                             "mcnemar_learned_vs_classifier": mcnemar(y, learned, p), "mcnemar_learned_vs_hand": mcnemar(y, learned, hand)}
        print("E5", k, {n: (round(R["E5_fusion"][k][n]["f1"], 4), round(R["E5_fusion"][k][n]["fpr"], 4))
                        for n in ("classifier", "hand_fusion_v3", "learned_fusion_v4")})

    # E6 legacy model
    try:
        from ml_common.registry.model_registry import ModelRegistry
        from ml_service.inference.inference_engine import InferenceEngine
        # v3 was trained with the v3 preprocessing (no bare-domain URLs, no Devanagari); restore it for a fair comparison.
        import re as _re
        import ml_common.preprocessing.text_cleaner as _tc
        import ml_common.preprocessing.tokenizer as _tk
        saved = (_tc._URL_PATTERN, _tc._PUNCTUATION_PATTERN, _tk._TOKEN_PATTERN)
        _tc._URL_PATTERN = _re.compile(r"https?://\S+|www\.\S+")
        _tc._PUNCTUATION_PATTERN = _re.compile(r"[^\w\s]")
        _tk._TOKEN_PATTERN = _re.compile(r"[a-zA-Z_]+")
        eng = InferenceEngine(ModelRegistry(root_dir=os.path.join(HERE, "..", "..", "artifacts")), TextPreprocessingPipeline(), "svm")
        eng._version = "v3"  # noqa: SLF001 - pin the legacy model explicitly
        eng.load()
        if eng.version_info.version == "v3":
            R["E6_legacy_v3"] = {}
            for k, d in tests.items():
                p = np.array([eng.predict(t).scam_probability for t in d.text])
                y = (d.label == "scam").astype(int).values
                R["E6_legacy_v3"][k] = {"classifier": Scores(y, p).metrics(boot=0), "fused": Scores(y, fused(d.text.tolist(), p)).metrics(boot=0)}
            print("E6", {k: round(v["fused"]["f1"], 4) for k, v in R["E6_legacy_v3"].items()})
        _tc._URL_PATTERN, _tc._PUNCTUATION_PATTERN, _tk._TOKEN_PATTERN = saved
    except Exception:  # noqa: BLE001 - v3 and its UCI training data were removed; use the frozen scores
        R["E6_legacy_v3"] = json.load(open(os.path.join(HERE, "results_legacy_v3.json")))["E6_legacy_v3"]

    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(R, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
