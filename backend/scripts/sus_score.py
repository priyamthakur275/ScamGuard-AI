"""Score a ScamGuard pilot from a Google Forms CSV export.

    python scripts/sus_score.py responses.csv

Expects the ten SUS statements (in the standard order, answers 1-5) and the
task columns from docs/v2/PILOT_KIT.md. Prints the SUS score (mean, 95% CI,
grade on the Sauro-Lewis curve), task success and the free-text comments.
Nothing is written; responses stay with whoever ran the pilot.
"""
from __future__ import annotations

import csv
import math
import statistics
import sys

SUS_PREFIX = "SUS"
GRADES = [(84.1, "A+"), (80.8, "A"), (78.9, "A-"), (77.2, "B+"), (74.1, "B"), (72.6, "B-"), (71.1, "C+"), (65.0, "C"), (62.7, "C-"), (51.7, "D"), (0, "F")]


def sus(answers: list[int]) -> float:
    if len(answers) != 10 or any(not 1 <= a <= 5 for a in answers):
        raise ValueError("SUS needs ten answers from 1 to 5")
    odd = sum(a - 1 for a in answers[0::2])
    even = sum(5 - a for a in answers[1::2])
    return (odd + even) * 2.5


def grade(score: float) -> str:
    return next(g for cut, g in GRADES if score >= cut)


def summarise(rows: list[dict]) -> dict:
    sus_cols = [c for c in rows[0] if c.strip().upper().startswith(SUS_PREFIX)]
    if len(sus_cols) != 10:
        raise ValueError(f"expected 10 SUS columns starting with 'SUS', found {len(sus_cols)}")
    scores = [sus([int(str(r[c]).strip()[0]) for c in sus_cols]) for r in rows]
    n, mean = len(scores), statistics.fmean(scores)
    half = 1.96 * statistics.stdev(scores) / math.sqrt(n) if n > 1 else float("nan")
    task_cols = [c for c in rows[0] if c.strip().upper().startswith("TASK")]
    tasks = {c: sum(str(r[c]).strip().lower().startswith(("yes", "correct", "right")) for r in rows) / n for c in task_cols}
    comments = [r[c] for r in rows for c in r if c.strip().upper().startswith("COMMENT") and str(r[c]).strip()]
    return {"participants": n, "sus_mean": mean, "sus_ci95": (mean - half, mean + half), "grade": grade(mean), "task_success": tasks, "comments": comments}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with open(sys.argv[1], newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    s = summarise(rows)
    print(f"Participants: {s['participants']}")
    print(f"SUS: {s['sus_mean']:.1f} (95% CI {s['sus_ci95'][0]:.1f}-{s['sus_ci95'][1]:.1f}), grade {s['grade']} (68 = average)")
    for c, v in s["task_success"].items():
        print(f"{c}: {100 * v:.0f}% succeeded")
    for c in s["comments"]:
        print("-", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
