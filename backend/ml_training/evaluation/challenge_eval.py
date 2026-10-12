"""Scores the production model on indian_challenge_set.csv (never trained on).

Reports both the raw model probability and the full pipeline (model +
threat scorer), so the two numbers shown in the app can be checked:

    python -m ml_training.evaluation.challenge_eval [--model svm]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry
from ml_service.inference.inference_engine import InferenceEngine
from ml_service.inference.threat_scorer import ThreatScorer

CHALLENGE = Path(__file__).resolve().parents[1] / "datasets" / "indian_challenge_set.csv"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="svm")
    ap.add_argument("--artifacts-dir", default="artifacts")
    ap.add_argument("--show", action="store_true", help="print every message with its scores")
    args = ap.parse_args(argv)

    engine = InferenceEngine(ModelRegistry(root_dir=args.artifacts_dir), TextPreprocessingPipeline(), args.model)
    engine.load()
    scorer = ThreatScorer()
    df = pd.read_csv(CHALLENGE)
    rows = []
    for text, label in zip(df.text, df.label):
        p = engine.predict(text).scam_probability
        tokens, _ = engine.transform(text)
        t = scorer.assess(p, tokens, text).threat_score
        rows.append((label == "scam", p, t, text))

    def report(name: str, idx: int) -> None:
        tp = sum(1 for r in rows if r[0] and r[idx] >= 0.5)
        fn = sum(1 for r in rows if r[0] and r[idx] < 0.5)
        fp = sum(1 for r in rows if not r[0] and r[idx] >= 0.5)
        tn = sum(1 for r in rows if not r[0] and r[idx] < 0.5)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        scam_scores = sorted(r[idx] for r in rows if r[0])
        legit_scores = sorted(r[idx] for r in rows if not r[0])
        print(f"{name:<22} acc={(tp + tn) / len(rows):.3f} precision={prec:.3f} recall={rec:.3f} f1={f1:.3f} "
              f"TP={tp} FN={fn} FP={fp} TN={tn} | median scam={scam_scores[len(scam_scores)//2]:.2f} "
              f"min scam={scam_scores[0]:.2f} | median legit={legit_scores[len(legit_scores)//2]:.2f} max legit={legit_scores[-1]:.2f}")

    print(f"model={engine.version_info.model_name} {engine.version_info.version} on {len(rows)} challenge messages")
    report("model probability", 1)
    report("threat score (final)", 2)
    if args.show:
        for is_scam, p, t, text in rows:
            flag = "" if (p >= 0.5) == is_scam else "  <-- model wrong"
            print(f"{'SCAM' if is_scam else 'OK  '} p={p:.2f} t={t:.2f}  {text[:90]}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
