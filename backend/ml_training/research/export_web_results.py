"""Export the deployed system's scores on the real test set for the website's
Research Lab page (frontend/public/research/test_scores.json).

    python -m ml_training.research.export_web_results

Uses the registered production artifact (logistic_regression v4) and the same
ThreatScorer as serving, so the page reproduces production_v4.json exactly:
the script refuses to write if the confusion matrix differs.
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd

from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_service.inference.threat_scorer import ThreatScorer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DS = os.path.join(HERE, "..", "datasets", "scamguard_in_2026", "scamguard_in_2026.csv")
ART = os.path.join(ROOT, "artifacts", "logistic_regression", "v4")
OUT = os.path.abspath(os.path.join(ROOT, "..", "frontend", "public", "research", "test_scores.json"))


def main() -> int:
    df = pd.read_csv(DS)
    test = df[df.split == "test"].reset_index(drop=True)
    pre = TextPreprocessingPipeline()
    vec = TfidfFeatureExtractor.load(os.path.join(ART, "vectorizer.joblib"))
    model = joblib.load(os.path.join(ART, "model.joblib"))
    texts = test.text.astype(str).tolist()
    p = model.predict_proba(vec.transform(pre.process_batch(texts)))[:, 1]
    sc = ThreatScorer()
    final = np.array([sc.assess(float(q), pre.process_to_tokens(t), t).threat_score for t, q in zip(texts, p)])
    y = (test.label == "scam").astype(int).values

    expected = json.load(open(os.path.join(HERE, "production_v4.json")))["tests"]["real_test"]
    for name, s in (("classifier", p), ("final_verdict", final)):
        yh = (s >= 0.5).astype(int)
        got = {"tp": int(((yh == 1) & (y == 1)).sum()), "fp": int(((yh == 1) & (y == 0)).sum()),
               "fn": int(((yh == 0) & (y == 1)).sum()), "tn": int(((yh == 0) & (y == 0)).sum())}
        want = {k: expected[name][k] for k in got}
        print(name, got, "OK" if got == want else f"MISMATCH, expected {want}")
        if got != want:
            return 1

    rows = [{"t": t, "y": int(l), "src": s, "sub": "" if pd.isna(sub) else str(sub), "p": round(float(a), 4), "f": round(float(b), 4)}
            for t, l, s, sub, a, b in zip(texts, y, test.source, test.subtype, p, final)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"model": "logistic_regression v4", "set": "ScamGuard-IN-2026 real test (unseen campaigns)", "rows": rows}, fh, ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUT, len(rows), "rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
