"""Recover the year of IMC'25 messages for the v2 temporal split.

IMC'25 keeps the timestamp shown on each reported screenshot in a free-text
``time`` column ("27/12/2021 9:51:58", "martes, 18 de enero de 2022 13:17",
"Today 14:58"). Only stamps with an explicit four-digit year are used; nothing
is guessed. Rows are matched to ScamGuard-IN-2026 with the same placeholder
restore, PII masking and key normalisation that ``build.py`` uses.

    bash fetch_sources.sh                      # downloads raw/imc25_smishing.csv
    python -m ml_training.datasets.scamguard_in_2026.imc_years

Writes ``imc_years.csv`` (key, year), which is committed so the temporal
experiment runs without the raw download.
"""

from __future__ import annotations

import os

import pandas as pd

from ml_training.datasets.scamguard_in_2026.build import norm_key, restore_placeholders
from ml_training.datasets.scamguard_in_2026.pii import mask_pii

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw", "imc25_smishing.csv")
OUT = os.path.join(HERE, "imc_years.csv")


def main() -> int:
    raw = pd.read_csv(RAW, low_memory=False)
    raw["year"] = pd.to_numeric(raw["time"].astype(str).str.extract(r"(20[12]\d)")[0], errors="coerce")
    raw = raw.dropna(subset=["year"])
    years: dict[str, int] = {}
    for t, y in zip(raw.text.astype(str), raw.year.astype(int)):
        r = restore_placeholders(t)
        for k in (norm_key(r), norm_key(mask_pii(r))):
            years[k] = min(years.get(k, y), y)
    ds = pd.read_csv(os.path.join(HERE, "scamguard_in_2026.csv"))
    imc = ds[ds.source == "imc25"]
    keys = imc.text.map(norm_key)
    out = pd.DataFrame({"key": keys, "year": keys.map(years)}).dropna().drop_duplicates("key")
    out["year"] = out.year.astype(int)
    out.sort_values(["year", "key"]).to_csv(OUT, index=False)
    print(f"dated {len(out)} of {len(imc)} IMC'25 rows -> {OUT}")
    print(out.year.value_counts().sort_index().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
