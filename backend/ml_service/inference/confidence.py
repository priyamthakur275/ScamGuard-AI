"""Confidence score calculation (step 17).

Confidence is deliberately modeled as a SEPARATE concept from scam
probability: a message scored at 0.51 and one scored at 0.99 both predict
"scam" (probability >= 0.5), but the model is far more *confident* about
the second. Confidence is the distance from the decision boundary (0.5),
rescaled to [0, 1] -- not the raw probability itself.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceConfig:
    decision_boundary: float = 0.5


class ConfidenceCalculator:
    """Converts a raw class probability into a confidence score."""

    def __init__(self, config: ConfidenceConfig | None = None):
        self._config = config or ConfidenceConfig()

    def calculate(self, scam_probability: float) -> float:
        """Returns a value in [0, 1]: 0 means the model is at its least
        certain (probability sitting exactly on the decision boundary),
        1 means maximally certain (probability at 0.0 or 1.0).
        """
        boundary = self._config.decision_boundary
        distance = abs(scam_probability - boundary)
        max_distance = max(boundary, 1 - boundary)
        if max_distance == 0:
            return 1.0
        confidence = distance / max_distance
        return round(min(max(confidence, 0.0), 1.0), 4)
