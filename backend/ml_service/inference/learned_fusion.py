"""Learned evidence fusion (ScamGuard v4).

The v3 ThreatScorer combined the classifier and the intent rules with hand-set
weights: ``logit = clip(logit p, ±4) + 5 (E_for - E_against)``. On real Indian SMS
those weights over-fire on genuine bank and brand messages that mention KYC,
"click" or a deadline. Here the same interpretable evidence is kept, but its
weights are learned from data:

    z = b + w0 * clip(logit p_oof, ±6) + Σ w_i * intent_i + Σ v_j * protective_j
        + u1 * genuine_transaction + u2 * genuine_notice
    score = sigmoid(z)

``p_oof`` is the classifier probability for a message the classifier did not see
in training (out-of-fold), so the fusion learns how far to trust the classifier on
unseen text. The weights are a small JSON artifact stored with the model version,
and every weight is readable: a positive intent weight means the pattern is
evidence of a scam in this data, a negative protective weight means evidence of a
genuine message.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass

from ml_service.inference.threat_scorer import (
    _INTENTS,
    _PROTECTIVE,
    ThreatScorer,
    is_genuine_notice,
    is_genuine_transaction,
)

INTENT_NAMES = sorted({n for n, _w, _rx in _INTENTS} | {"decoy_warning"})
PROTECTIVE_NAMES = sorted({n for n, _w, _rx in _PROTECTIVE})
FLAG_NAMES = ["genuine_transaction", "genuine_notice"]
LOGIT_CAP = 6.0


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return max(-LOGIT_CAP, min(LOGIT_CAP, math.log(p / (1 - p))))


def evidence(text: str) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    text = " ".join(str(text).split())
    found, protective = ThreatScorer.intents(text)
    flags = {
        "genuine_transaction": float(is_genuine_transaction(text, found, protective)),
        "genuine_notice": float(is_genuine_notice(text, found, protective)),
    }
    return found, protective, flags


def feature_vector(text: str, p: float) -> list[float]:
    found, protective, flags = evidence(text)
    return ([_logit(p)] + [1.0 if n in found else 0.0 for n in INTENT_NAMES]
            + [1.0 if n in protective else 0.0 for n in PROTECTIVE_NAMES] + [flags[n] for n in FLAG_NAMES])


def feature_names() -> list[str]:
    return ["classifier_logit"] + [f"intent:{n}" for n in INTENT_NAMES] + [f"protective:{n}" for n in PROTECTIVE_NAMES] + [f"flag:{n}" for n in FLAG_NAMES]


@dataclass(frozen=True)
class LearnedFusion:
    bias: float
    weights: dict[str, float]

    def score(self, text: str, p: float) -> float:
        z = self.bias
        for name, x in zip(feature_names(), feature_vector(text, p)):
            if x:
                z += self.weights.get(name, 0.0) * x
        return 1 / (1 + math.exp(-z))

    def contributions(self, text: str, p: float) -> dict[str, float]:
        return {n: round(self.weights.get(n, 0.0) * x, 4) for n, x in zip(feature_names(), feature_vector(text, p)) if x}

    def to_json(self) -> dict:
        return {"version": 1, "bias": self.bias, "weights": self.weights}

    @classmethod
    def from_json(cls, d: dict) -> "LearnedFusion":
        return cls(bias=float(d["bias"]), weights={k: float(v) for k, v in d["weights"].items()})

    @classmethod
    def load(cls, path: str) -> "LearnedFusion | None":
        if not os.path.exists(path):
            return None
        with open(path) as fh:
            return cls.from_json(json.load(fh))


def fit(texts: list[str], p_oof: list[float], labels: list[int], C: float = 1.0) -> LearnedFusion:
    from sklearn.linear_model import LogisticRegression

    X = [feature_vector(t, p) for t, p in zip(texts, p_oof)]
    m = LogisticRegression(C=C, max_iter=5000, class_weight="balanced").fit(X, labels)
    return LearnedFusion(bias=float(m.intercept_[0]), weights={n: float(w) for n, w in zip(feature_names(), m.coef_[0])})
