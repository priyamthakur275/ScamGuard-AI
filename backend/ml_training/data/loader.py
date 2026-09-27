"""Dataset loading.

Single responsibility: turn one or more raw CSV files on disk into a
single, unified in-memory DataFrame with exactly the columns the rest of
the pipeline expects (`text`, `label`). Column-name mapping is
configurable so heterogeneous source datasets (different column names in
Kaggle vs. UCI vs. SpamAssassin exports) can all be normalized here,
before validation ever sees them.
"""
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


class DatasetLoadError(Exception):
    pass


@dataclass(frozen=True)
class DatasetSource:
    """One raw CSV file plus how to map its columns onto the canonical
    `text`/`label` schema.
    """

    path: str
    text_column: str = "text"
    label_column: str = "label"
    encoding: str = "utf-8"


@dataclass(frozen=True)
class LoaderConfig:
    sources: list[DatasetSource] = field(default_factory=list)
    drop_duplicates: bool = True
    drop_empty_text: bool = True


class DatasetLoader:
    """Loads and merges one or more labeled message datasets."""

    def __init__(self, config: LoaderConfig):
        if not config.sources:
            raise ValueError("LoaderConfig must include at least one DatasetSource")
        self._config = config

    def load(self) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []

        for source in self._config.sources:
            frames.append(self._load_single(source))

        combined = pd.concat(frames, ignore_index=True)

        if self._config.drop_empty_text:
            is_missing = combined["text"].isna()
            is_blank = combined["text"].astype(str).str.strip() == ""
            combined = combined[~(is_missing | is_blank)]

        if self._config.drop_duplicates:
            combined = combined.drop_duplicates(subset=["text"])

        combined = combined.reset_index(drop=True)
        return combined

    @staticmethod
    def _load_single(source: DatasetSource) -> pd.DataFrame:
        path = Path(source.path)
        if not path.exists():
            raise DatasetLoadError(f"Dataset file not found: {source.path}")

        try:
            raw = pd.read_csv(path, encoding=source.encoding)
        except Exception as exc:  # noqa: BLE001 - surfaced as a domain error
            raise DatasetLoadError(f"Failed to read '{source.path}': {exc}") from exc

        missing = {source.text_column, source.label_column} - set(raw.columns)
        if missing:
            raise DatasetLoadError(
                f"'{source.path}' is missing required column(s): {sorted(missing)}"
            )

        normalized = raw[[source.text_column, source.label_column]].rename(
            columns={source.text_column: "text", source.label_column: "label"}
        )
        normalized["text"] = normalized["text"].fillna("").astype(str)
        normalized["label"] = normalized["label"].astype(str).str.strip().str.lower()
        return normalized
