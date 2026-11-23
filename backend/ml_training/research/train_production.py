"""Train and register the production model (v5) on ScamGuard-IN-2026.

    python -m ml_training.research.train_production [--no-promote]

Model: logistic regression on word (1-2) + character (2-5, within words) TF-IDF,
chosen on the dev split (see results.md). Trained on train + dev (real and
synthetic) plus the synthetic Hinglish/Hindi training rows (v2); every message
passes through ``deobfuscate`` first, exactly as the app does at serving time.
The test splits are only scored, never trained on.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from ml_common.domain.value_objects import ModelMetrics
from ml_common.features.tfidf_vectorizer import TfidfConfig, TfidfFeatureExtractor
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.preprocessing.robust import deobfuscate
from ml_training.datasets.scamguard_in_2026 import hinglish
from ml_common.registry.model_registry import ModelRegistry
from ml_training.research.run_experiments import DS, Scores, fused, load_challenge

HERE = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS = os.path.join(HERE, "..", "..", "artifacts")
MODEL_NAME, VERSION = "logistic_regression", "v5"
TFIDF = TfidfConfig(max_features=30000, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True, char_ngram_range=(2, 5), char_max_features=60000)
C = 16.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-promote", action="store_true")
    a = ap.parse_args(argv)

    df = pd.read_csv(DS)
    train = pd.concat([df[df.split.isin(["train", "dev"])], pd.DataFrame(hinglish.train_rows())], ignore_index=True)
    tests = {"real_test": df[df.split == "test"], "challenge": load_challenge()}
    if (df.split == "test_2026").any():
        tests["test_2026"] = df[df.split == "test_2026"]
    tests["hinglish_b"] = pd.DataFrame(hinglish.test_b_rows())

    pre = TextPreprocessingPipeline()
    vec = TfidfFeatureExtractor(TFIDF)
    X = vec.fit_transform(pre.process_batch([deobfuscate(t) for t in train.text.astype(str)]))
    y = (train.label == "scam").astype(int).values
    model = LogisticRegression(C=C, max_iter=5000, class_weight="balanced").fit(X, y)

    report = {"model": MODEL_NAME, "version": VERSION, "train_rows": int(len(train)), "vocabulary": vec.vocabulary_size, "C": C, "tests": {}}
    for k, d in tests.items():
        texts = [deobfuscate(t) for t in d.text.astype(str)]
        p = model.predict_proba(vec.transform(pre.process_batch(texts)))[:, 1]
        yy = (d.label == "scam").astype(int).values
        report["tests"][k] = {"classifier": Scores(yy, p).metrics(boot=1000), "final_verdict": Scores(yy, fused(texts, p)).metrics(boot=1000)}
        m = report["tests"][k]["final_verdict"]
        print(f"{k:10s} n={m['n']} final: acc={m['accuracy']:.4f} f1={m['f1']:.4f} precision={m['precision']:.4f} recall={m['recall']:.4f} fpr={m['fpr']:.4f}")

    r = report["tests"]["real_test"]["classifier"]
    metrics = ModelMetrics(accuracy=r["accuracy"], precision=r["precision"], recall=r["recall"], f1=r["f1"], roc_auc=r.get("roc_auc", 0.0),
                           false_positive_rate=r["fpr"], true_positives=r["tp"], true_negatives=r["tn"], false_positives=r["fp"], false_negatives=r["fn"])
    with tempfile.TemporaryDirectory() as tmp:
        mp, vp = os.path.join(tmp, "model.joblib"), os.path.join(tmp, "vectorizer.joblib")
        joblib.dump(model, mp)
        vec.save(vp)
        reg = ModelRegistry(root_dir=ARTIFACTS)
        reg.register(MODEL_NAME, VERSION, mp, vp, metrics, train_rows=int(len(train)), test_rows=int(len(tests["real_test"])))
        if not a.no_promote:
            reg.promote(MODEL_NAME, VERSION)
    with open(os.path.join(HERE, f"production_{VERSION}.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("registered", MODEL_NAME, VERSION, "" if a.no_promote else "(production)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
