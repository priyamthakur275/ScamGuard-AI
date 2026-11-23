"""Add real Hindi / Hinglish messages that the team collected (v2).

    python -m ml_training.datasets.scamguard_in_2026.add_real_indic collected.csv [more.csv ...]

Input: CSV with a ``text`` column and a ``label`` column (scam / genuine; spam, ham,
legitimate, 1 and 0 are also accepted). Optional ``note`` column. See
docs/v2/COLLECT_REAL_HINDI.md for how to collect them.

What it does, in order:
  1. replaces phone numbers, account numbers, codes, emails and UPI IDs with random
     stand-ins (the dataset's ``pii.mask_pii``). Names are NOT removed: collectors must
     delete names before sharing (see the guide)
  2. drops rows with no label, very short texts and exact duplicates
  3. drops anything already in ScamGuard-IN-2026, in the synthetic Hinglish banks, or
     near-identical to the frozen 77-message real Hindi test set (real_indic_test.csv),
     so that test set stays clean
  4. groups near-duplicates (character 5-gram Jaccard >= 0.6), the same idea as the
     dataset's campaign grouping, and splits whole groups 50/50 into train and test,
     stratified by label (seed 42)
  5. merges with any earlier collected rows and writes real_indic_collected.csv

Afterwards ``train_production`` trains on the collected train rows and
``v2_experiments`` reports the collected test rows (X8b) next to the frozen test (X8).
"""

from __future__ import annotations

import argparse
import os
import random
import re

import pandas as pd

from ml_training.datasets.scamguard_in_2026 import hinglish
from ml_training.datasets.scamguard_in_2026.build import norm_key
from ml_training.datasets.scamguard_in_2026.pii import mask_pii

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "real_indic_collected.csv")
FROZEN = os.path.join(HERE, "real_indic_test.csv")
LABELS = {"scam": "scam", "spam": "scam", "fraud": "scam", "1": "scam", "yes": "scam",
          "genuine": "legitimate", "legitimate": "legitimate", "ham": "legitimate", "real": "legitimate", "0": "legitimate", "no": "legitimate"}


def shingles(t: str) -> set[str]:
    t = re.sub(r"\d", "0", " ".join(str(t).lower().split()))
    return {t[i:i + 5] for i in range(max(1, len(t) - 4))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def group_ids(texts: list[str], prefix: str, start: int = 0) -> list[str]:
    sh = [shingles(t) for t in texts]
    gid = list(range(len(texts)))
    for i in range(len(texts)):
        for j in range(i):
            if jaccard(sh[i], sh[j]) >= 0.6:
                gid[i] = gid[j]
                break
    return [f"{prefix}{start + g:04d}" for g in gid]


def clean(frames: list[pd.DataFrame]) -> tuple[pd.DataFrame, dict]:
    d = pd.concat(frames, ignore_index=True)
    cols = {c.lower().strip(): c for c in d.columns}
    if "text" not in cols or "label" not in cols:
        raise SystemExit(f"need 'text' and 'label' columns, found {list(d.columns)}")
    d = pd.DataFrame({"text": d[cols["text"]].astype(str), "label": d[cols["label"]].astype(str).str.strip().str.lower().map(LABELS),
                      "note": d[cols["note"]].astype(str) if "note" in cols else ""})
    stats = {"rows_in": int(len(d))}
    d = d.dropna(subset=["label"])
    stats["unlabelled_dropped"] = stats["rows_in"] - len(d)
    d["text"] = [" ".join(mask_pii(t).split()) for t in d.text]
    d = d[d.text.str.len() >= 15]
    d["key"] = d.text.map(norm_key)
    n = len(d)
    d = d.drop_duplicates("key")
    stats["duplicates_dropped"] = n - len(d)
    ds = pd.read_csv(os.path.join(HERE, "scamguard_in_2026.csv"))
    seen = set(ds.text.map(norm_key))
    for rows in (hinglish.train_rows(), hinglish.dev_rows(), hinglish.test_rows(), hinglish.test_b_rows()):
        seen |= {norm_key(r["text"]) for r in rows}
    n = len(d)
    d = d[~d.key.isin(seen)]
    stats["already_in_dataset_dropped"] = n - len(d)
    frozen = [shingles(t) for t in pd.read_csv(FROZEN).text]
    n = len(d)
    d = d[[max((jaccard(shingles(t), f) for f in frozen), default=0) < 0.6 for t in d.text]]
    stats["near_frozen_test_dropped"] = n - len(d)
    return d.reset_index(drop=True), stats


def split(d: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    r = random.Random(seed)
    d["split"] = ""
    for lab in ("scam", "legitimate"):
        groups = sorted(d[d.label == lab].group.unique())
        r.shuffle(groups)
        half = set(groups[: (len(groups) + 1) // 2])
        d.loc[(d.label == lab) & d.group.isin(half), "split"] = "train"
        d.loc[(d.label == lab) & ~d.group.isin(half), "split"] = "test"
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    a = ap.parse_args(argv)
    new, stats = clean([pd.read_csv(f) for f in a.csv])
    old = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame(columns=["text", "label", "group", "split", "note"])
    if len(old):
        okeys = set(old.text.map(norm_key))
        new = new[~new.key.isin(okeys)]
        osh = [shingles(t) for t in old.text]
        # a new message that joins an existing group keeps that group's split
        join = [next((i for i, s in enumerate(osh) if jaccard(shingles(t), s) >= 0.6), None) for t in new.text]
        new["group"] = [old.group.iloc[j] if j is not None else None for j in join]
        new["split"] = [old.split.iloc[j] if j is not None else None for j in join]
    else:
        new["group"], new["split"] = None, None
    fresh = new[new.group.isna()].copy()
    start = len(set(old.group)) if len(old) else 0
    fresh["group"] = group_ids(fresh.text.tolist(), "col_", start)
    fresh = split(fresh)
    out = pd.concat([old, new[new.group.notna() & new.split.notna()], fresh], ignore_index=True)[["text", "label", "group", "split", "note"]]
    out.to_csv(OUT, index=False)
    stats["added"] = int(len(new))
    stats["total_collected"] = int(len(out))
    print(stats)
    print(out.groupby(["split", "label"]).size().unstack(fill_value=0).to_string())
    print(f"groups: {out.group.nunique()} -> {OUT}")
    print("next: python -m ml_training.research.train_production && python -m ml_training.research.v2_experiments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
