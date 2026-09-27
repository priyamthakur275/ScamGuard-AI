"""Dataset validation.

Runs after loading and before preprocessing. Fails fast with a specific,
actionable error rather than letting a malformed dataset silently degrade
model quality three stages later.
"""
from dataclasses import dataclass, field

import pandas as pd


class DatasetValidationError(Exception):
    """Raised when the dataset fails a hard validation rule."""


@dataclass(frozen=True)
class ValidationConfig:
    allowed_labels: frozenset[str] = field(
        default_factory=lambda: frozenset({"legitimate", "spam", "phishing", "scam"})
    )
    min_rows: int = 10
    max_class_imbalance_ratio: float = 20.0
    min_text_length: int = 3


@dataclass(frozen=True)
class ValidationReport:
    """Non-fatal observations surfaced alongside a passing validation,
    so a human (or a CI gate) can still see data-quality warnings.
    """

    row_count: int
    label_distribution: dict
    warnings: list[str]


class DatasetValidator:
    """Validates a DataFrame produced by `DatasetLoader`."""

    def __init__(self, config: ValidationConfig | None = None):
        self._config = config or ValidationConfig()

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        self._require_columns(df)
        self._require_min_rows(df)
        self._require_no_nulls(df)
        self._require_known_labels(df)
        self._require_minimum_text_length(df)

        warnings = self._check_class_balance(df)

        return ValidationReport(
            row_count=len(df),
            label_distribution=df["label"].value_counts().to_dict(),
            warnings=warnings,
        )

    # -- hard checks (raise) ---------------------------------------------

    @staticmethod
    def _require_columns(df: pd.DataFrame) -> None:
        missing = {"text", "label"} - set(df.columns)
        if missing:
            raise DatasetValidationError(f"Dataset is missing required column(s): {sorted(missing)}")

    def _require_min_rows(self, df: pd.DataFrame) -> None:
        if len(df) < self._config.min_rows:
            raise DatasetValidationError(
                f"Dataset has only {len(df)} row(s); at least {self._config.min_rows} are required"
            )

    @staticmethod
    def _require_no_nulls(df: pd.DataFrame) -> None:
        null_counts = df[["text", "label"]].isnull().sum()
        if null_counts.sum() > 0:
            raise DatasetValidationError(f"Dataset contains null values: {null_counts.to_dict()}")

    def _require_known_labels(self, df: pd.DataFrame) -> None:
        unexpected = set(df["label"].unique()) - self._config.allowed_labels
        if unexpected:
            raise DatasetValidationError(
                f"Dataset contains unexpected label(s): {sorted(unexpected)}. "
                f"Allowed labels are: {sorted(self._config.allowed_labels)}"
            )

    def _require_minimum_text_length(self, df: pd.DataFrame) -> None:
        too_short = df[df["text"].str.strip().str.len() < self._config.min_text_length]
        if not too_short.empty:
            raise DatasetValidationError(
                f"{len(too_short)} row(s) have text shorter than "
                f"{self._config.min_text_length} characters"
            )

    # -- soft checks (warn) -----------------------------------------------

    def _check_class_balance(self, df: pd.DataFrame) -> list[str]:
        warnings: list[str] = []
        counts = df["label"].value_counts()

        if len(counts) < 2:
            warnings.append("Dataset contains fewer than 2 distinct labels")
            return warnings

        ratio = counts.max() / counts.min()
        if ratio > self._config.max_class_imbalance_ratio:
            warnings.append(
                f"Class imbalance ratio is {ratio:.1f}:1 (majority/minority), "
                f"exceeding the configured threshold of {self._config.max_class_imbalance_ratio}:1. "
                "Consider class weighting or resampling."
            )

        return warnings
