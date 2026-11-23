"""ScamGuard v2 experiments. Every v2 number comes from this script.

    python -m ml_training.research.v2_experiments [--quick]

Writes ml_training/research/results_v2.json and results_v2.md.

Systems (same learner throughout: logistic regression, C=16, word 1-2 + char 2-5 TF-IDF,
trained on train+dev; the risk engine is the current ThreatScorer, including the v2
Hindi/Hinglish intent rules):
  v1_reported  the exam model scored the way the v1 report scored it (raw text)
  v1_deployed  the exam model scored the way the live v1 app scored it: the app appended
               an English "Detected concepts" summary to the text before the model, which
               the model never saw in training (a train/serve mismatch found in v2)
  v2           v1 data + synthetic Hinglish/Hindi training rows (equal weight); every message
               passes through ``deobfuscate``; the concept summary is kept for display only
               and is no longer fed to the model

Settings chosen on the dev split and the Hinglish dev templates, never on a test set.

X1  v1 vs v2 on the real test set, challenge set, 2025-26 advisories and the
    held-out Hinglish/Hindi challenge set, with bootstrap CIs and McNemar tests
X2  Adversarial robustness: six evasion attacks applied to the real test set
X3  Temporal drift: train on campaigns first seen up to 2020, test on campaigns
    first seen in 2022-23, against random campaign hold-outs of the same size
X4  Calibration (ECE, reliability bins) and an "uncertain - review" band
X5  Fusion ablation: what each part of the risk engine adds
X6  Simple-rule baselines ("has a link", "has a link or phone number")
X7  Latency of the full deployed path on CPU
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import time

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from ml_common.features.tfidf_vectorizer import TfidfConfig, TfidfFeatureExtractor
from ml_common.preprocessing.multilingual import normalize_for_analysis
from ml_common.preprocessing.robust import deobfuscate
from ml_service.inference import threat_scorer as ts
from ml_training.research.v1_frozen import threat_scorer_v1 as ts_v1
from ml_training.datasets.scamguard_in_2026 import hinglish
from ml_training.research.run_experiments import DS, PRE, Scores, load_challenge, mcnemar

HERE = os.path.dirname(os.path.abspath(__file__))
YEARS = os.path.join(HERE, "..", "datasets", "scamguard_in_2026", "imc_years.csv")
CROSS_B = os.path.join(HERE, "..", "..", "..", "research", "cross_domain", "data", "clean")
TFIDF = TfidfConfig(max_features=30000, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True, char_ngram_range=(2, 5), char_max_features=60000)
SEED = 2026
BOOT = 1000


# ------------------------------------------------------------------------------------------ model
class System:
    """One trained system, scored exactly the way the deployed app scores a message."""

    def __init__(self, train: pd.DataFrame, robust: bool, summary: bool = False, engine=ts):
        self.robust, self.summary, self.engine = robust, summary, engine
        self.vec = TfidfFeatureExtractor(TFIDF)
        X = self.vec.fit_transform(PRE.process_batch(self._norm(train.text, fitting=True)))
        y = (train.label == "scam").astype(int).values
        self.clf = LogisticRegression(C=16.0, max_iter=5000, class_weight="balanced").fit(X, y)

    def _norm(self, texts, fitting: bool = False) -> list[str]:
        out = [str(t) for t in texts]
        if self.robust:
            out = [deobfuscate(t) for t in out]
        if self.summary and not fitting:  # v1 app: summary appended at serving time only
            out = [normalize_for_analysis(t) for t in out]
        return out

    def score(self, texts) -> tuple[np.ndarray, np.ndarray, list[str]]:
        t = self._norm(texts)
        p = self.clf.predict_proba(self.vec.transform(PRE.process_batch(t)))[:, 1]
        sc = self.engine.ThreatScorer()
        s = np.array([sc.assess(float(pp), PRE.process_to_tokens(x), x).threat_score for x, pp in zip(t, p)])
        return p, s, t


def lab(d: pd.DataFrame) -> np.ndarray:
    return (d.label == "scam").astype(int).values


def summary(m: dict) -> dict:
    keys = ("n", "accuracy", "precision", "recall", "f1", "fpr", "roc_auc", "f1_ci", "fpr_ci", "tp", "fp", "fn", "tn")
    return {k: m[k] for k in keys if k in m}


# ------------------------------------------------------------------------------------------ attacks
TRIGGERS = re.compile(r"\b(kyc|otp|click|account|acct|verify|blocked|block|update|pin|urgent|link|bank|reward|prize|won|win|"
                      r"claim|refund|password|suspend\w*|expire\w*|free|cashback|lottery|login|card|upi|pan|aadhaar)\b", re.I)
CYR = {"a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х", "y": "у", "i": "і", "A": "А", "E": "Е", "O": "О", "C": "С",
       "P": "Р", "K": "К", "M": "М", "T": "Т", "B": "В", "H": "Н", "X": "Х", "Y": "Ү", "I": "І"}
LEET = {"o": "0", "O": "0", "e": "3", "E": "3", "a": "4", "A": "4", "i": "1", "I": "1", "s": "5", "S": "5"}


def _homoglyph(w, r):
    return "".join(CYR.get(c, c) if r.random() < 0.7 else c for c in w)


def _zero_width(w, r):
    return w[:1] + "".join("​" + c for c in w[1:])


def _spaced(w, r):
    return " ".join(w)


def _leet(w, r):
    out = [LEET.get(c, c) for c in w]
    return "".join(out) if out != list(w) else w


def _word_attack(fn):
    def apply(text, r):
        return TRIGGERS.sub(lambda m: fn(m.group(0), r), text)
    return apply


def _defang(text, r):
    t = re.sub(r"\bhttp", "hxxp", text, flags=re.I)
    return re.sub(r"(?<=[a-z0-9])\.(?=(?:com|in|ly|xyz|top|co|net|org|me|gy|gd|site|online|click|vip|live|info|example)\b)", "[.]", t, flags=re.I)


def _combo(text, r):
    fns = [_homoglyph, _zero_width, _leet]
    t = TRIGGERS.sub(lambda m: r.choice(fns)(m.group(0), r), text)
    return _defang(t, r)


ATTACKS = {"homoglyph": _word_attack(_homoglyph), "zero_width": _word_attack(_zero_width), "spaced_letters": _word_attack(_spaced),
           "leetspeak": _word_attack(_leet), "defanged_url": _defang, "combined": _combo}


# ------------------------------------------------------------------------------------------ helpers
def ece(y, p, bins=15) -> tuple[float, list[dict]]:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    e, table = 0.0, []
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        conf, acc = float(p[m].mean()), float(y[m].mean())
        e += m.mean() * abs(conf - acc)
        table.append({"bin": f"{edges[b]:.2f}-{edges[b + 1]:.2f}", "n": int(m.sum()), "mean_predicted": round(conf, 4), "fraction_scam": round(acc, 4)})
    return float(e), table


_URL = re.compile(r"https?://|www\.|\b(?:[a-z0-9-]+\.)+(?:com|in|ly|me|co|org|net|xyz|top|link|gy|gd|io|app|info|site|online|click|live|shop|vip|cc|to|example)\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)|\b1800[-\s]?\d{3}[-\s]?\d{4}\b")


def fusion_variants(texts, probs) -> dict[str, np.ndarray]:
    """Re-implements ThreatScorer.assess with parts switched off (same constants)."""
    out = {k: [] for k in ("classifier_only", "rules_only", "plus_intents", "plus_protective", "full", "full_without_logit_clip")}
    for t, p in zip(texts, probs):
        found, prot = ts.ThreatScorer.intents(t)
        ef = sum(found.values())
        if set(found) <= {"deadline", "impersonation", "account_threat", "link_with_action", "call_private_number"}:
            ef *= 0.5
        ea = sum(prot.values()) if ef < 0.5 else 0.5 * sum(prot.values())
        raw = ts._logit(float(p))
        clip = max(-4.0, min(4.0, raw))
        sig = lambda z: 1 / (1 + math.exp(-z))
        gen = ts.is_genuine_transaction(t, found, prot) or ts.is_genuine_notice(t, found, prot)
        cap = lambda v: min(v, ts.GENUINE_TRANSACTION_CAP) if gen else v
        out["classifier_only"].append(float(p))
        out["rules_only"].append(cap(sig(5.0 * (ef - ea))))
        out["plus_intents"].append(sig(clip + 5.0 * ef))
        out["plus_protective"].append(sig(clip + 5.0 * (ef - ea)))
        out["full"].append(cap(sig(clip + 5.0 * (ef - ea))))
        out["full_without_logit_clip"].append(cap(sig(raw + 5.0 * (ef - ea))))
    return {k: np.array(v) for k, v in out.items()}


def campaign_years(df: pd.DataFrame) -> pd.Series:
    from ml_training.datasets.scamguard_in_2026.build import norm_key
    yrs = pd.read_csv(YEARS).set_index("key").year
    row_year = df.text.map(norm_key).map(yrs)
    imc = df.source == "imc25"
    return row_year[imc].groupby(df.campaign[imc]).min()


def load_cross_b() -> pd.DataFrame | None:
    """Dataset B of the cross-domain study (India SMS, cleaned). Only the rule baselines are
    reported on it: ScamGuard-IN-2026 contains India SMS rows, so a ScamGuard score here would leak."""
    f = os.path.join(CROSS_B, "dataset_B_india_clean.csv")
    if not os.path.exists(f):
        return None
    d = pd.read_csv(f)
    return pd.DataFrame({"text": d.message.astype(str), "label": np.where(d.label.astype(int) == 1, "scam", "legitimate")})


# ------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    global BOOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    BOOT = 200 if a.quick else 1000
    t0 = time.time()

    df = pd.read_csv(DS)
    train = df[df.split.isin(["train", "dev"])]
    hin_train = pd.DataFrame(hinglish.train_rows())
    hin_test = pd.DataFrame(hinglish.test_rows())
    hin_test_b = pd.DataFrame(hinglish.test_b_rows())
    overlap = (set(hin_train.text) & (set(hin_test.text) | set(hin_test_b.text)))
    tests = {"real_test": df[df.split == "test"], "challenge": load_challenge(), "test_2026": df[df.split == "test_2026"],
             "hinglish_a_dev_check": hin_test, "hinglish_b_final": hin_test_b}
    R: dict = {"data": {"train_rows_v1": int(len(train)), "hinglish_train_rows": int(len(hin_train)), "hinglish_test_rows": int(len(hin_test)),
                        "hinglish_train_test_exact_overlap": len(overlap), "test_sizes": {k: int(len(v)) for k, v in tests.items()}}}

    print("training v1 and v2 ...", flush=True)
    v1r = System(train, robust=False, engine=ts_v1)
    v1 = System(train, robust=False, summary=True, engine=ts_v1)
    v1.vec, v1.clf = v1r.vec, v1r.clf  # same trained model, different serving path
    v2 = System(pd.concat([train, hin_train], ignore_index=True), robust=True)
    R["data"]["vocabulary"] = {"v1": v1.vec.vocabulary_size, "v2": v2.vec.vocabulary_size}

    # X1 -----------------------------------------------------------------------------------
    X1, cache = {}, {}
    for k, d in tests.items():
        y = lab(d)
        p0, s0, _ = v1r.score(d.text)
        p1, s1, t1 = v1.score(d.text)
        p2, s2, t2 = v2.score(d.text)
        cache[k] = (y, p1, s1, p2, s2, t2)
        X1[k] = {"v1_reported": {"classifier": summary(Scores(y, p0).metrics(boot=BOOT)), "final": summary(Scores(y, s0).metrics(boot=BOOT))},
                 "v1": {"classifier": summary(Scores(y, p1).metrics(boot=BOOT)), "final": summary(Scores(y, s1).metrics(boot=BOOT))},
                 "v2": {"classifier": summary(Scores(y, p2).metrics(boot=BOOT)), "final": summary(Scores(y, s2).metrics(boot=BOOT))},
                 "mcnemar_final_v1_vs_v2": mcnemar(y, s1, s2)}
        if "template" in d:
            tpl = pd.DataFrame({"t": d.template.values, "y": y, "ok1": (s1 >= 0.5) == y, "ok2": (s2 >= 0.5) == y}).groupby("t").agg(y=("y", "first"), ok1=("ok1", "mean"), ok2=("ok2", "mean"))
            X1[k]["per_template"] = {"templates": int(len(tpl)), "v1_templates_mostly_right": int((tpl.ok1 >= 0.5).sum()), "v2_templates_mostly_right": int((tpl.ok2 >= 0.5).sum()),
                                     "v2_failed_templates": [{"template": i, "label": "scam" if r.y else "genuine", "accuracy": round(float(r.ok2), 3)} for i, r in tpl[tpl.ok2 < 0.5].iterrows()]}
        print(f"X1 {k:20s} v1 F1 {X1[k]['v1']['final']['f1']:.4f} FPR {X1[k]['v1']['final']['fpr']:.4f} | "
              f"v2 F1 {X1[k]['v2']['final']['f1']:.4f} FPR {X1[k]['v2']['final']['fpr']:.4f}", flush=True)
    R["X1_main"] = X1

    # X2 -----------------------------------------------------------------------------------
    X2 = {}
    d = tests["real_test"]
    y = lab(d)
    for name, fn in ATTACKS.items():
        r = random.Random(SEED)
        adv = [fn(t, r) for t in d.text.astype(str)]
        changed = float(np.mean([x != t for x, t in zip(adv, d.text.astype(str))]))
        row = {"messages_changed": round(changed, 4)}
        for tag, sysm in (("v1", v1), ("v2", v2)):
            _, s, _ = sysm.score(adv)
            m = Scores(y, s).metrics(boot=0)
            row[tag] = {"recall": m["recall"], "fpr": m["fpr"], "f1": m["f1"]}
        X2[name] = row
        print(f"X2 {name:15s} v1 recall {row['v1']['recall']:.4f} | v2 recall {row['v2']['recall']:.4f}", flush=True)
    X2["clean"] = {"v1": {k: X1["real_test"]["v1"]["final"][k] for k in ("recall", "fpr", "f1")},
                   "v2": {k: X1["real_test"]["v2"]["final"][k] for k in ("recall", "fpr", "f1")}}
    R["X2_adversarial"] = X2

    # X3 -----------------------------------------------------------------------------------
    cy = campaign_years(df)
    future = set(cy[cy >= 2022].index)
    gap = set(cy[cy == 2021].index)
    future_scam = df[df.campaign.isin(future) & (df.label == "scam")]
    genuine_test = tests["real_test"][tests["real_test"].label == "legitimate"]
    tr_t = train[~train.campaign.isin(future | gap)]
    sys_t = System(tr_t, robust=True)
    _, s_f, _ = sys_t.score(future_scam.text)
    _, s_g, _ = sys_t.score(genuine_test.text)
    X3 = {"dated_campaigns": int(len(cy)), "campaigns_by_first_year": {str(int(k)): int(v) for k, v in cy.value_counts().sort_index().items()},
          "future_campaigns": len(future), "future_scam_messages": int(len(future_scam)), "train_rows": int(len(tr_t)),
          "temporal": {"recall_future_scams": float((s_f >= 0.5).mean()), "fpr_real_genuine": float((s_g >= 0.5).mean())}, "random_holdout": []}
    dated = sorted(set(cy.index) - gap)
    n_hold = len(future)
    for seed in (42, 123, 2026):
        hold = set(random.Random(seed).sample(dated, n_hold))
        held = df[df.campaign.isin(hold) & (df.label == "scam")]
        sys_r = System(train[~train.campaign.isin(hold | gap)], robust=True)
        _, s_h, _ = sys_r.score(held.text)
        _, s_hg, _ = sys_r.score(genuine_test.text)
        X3["random_holdout"].append({"seed": seed, "scam_messages": int(len(held)), "recall": float((s_h >= 0.5).mean()), "fpr_real_genuine": float((s_hg >= 0.5).mean())})
    X3["random_holdout_mean_recall"] = float(np.mean([r["recall"] for r in X3["random_holdout"]]))
    print(f"X3 temporal recall {X3['temporal']['recall_future_scams']:.4f} vs random {X3['random_holdout_mean_recall']:.4f}", flush=True)
    R["X3_temporal"] = X3

    # X4 -----------------------------------------------------------------------------------
    y, _, _, p2, s2, _ = cache["real_test"]
    e_p, bins_p = ece(y, p2)
    e_s, bins_s = ece(y, s2)
    band = {}
    for lo, hi in ((0.4, 0.6), (0.3, 0.7), (0.2, 0.8)):
        inside = (s2 >= lo) & (s2 < hi)
        wrong = (s2 >= 0.5).astype(int) != y
        band[f"{lo}-{hi}"] = {"share_flagged_for_review": float(inside.mean()), "errors_inside": int((wrong & inside).sum()),
                              "errors_outside": int((wrong & ~inside).sum()), "accuracy_outside": float(1 - wrong[~inside].mean()),
                              "total_errors": int(wrong.sum())}
    R["X4_calibration"] = {"ece_classifier": e_p, "ece_final": e_s, "reliability_classifier": bins_p, "reliability_final": bins_s, "review_band": band}
    print(f"X4 ECE classifier {e_p:.4f} final {e_s:.4f}", flush=True)

    # X5 -----------------------------------------------------------------------------------
    X5 = {}
    for k in ("real_test", "challenge", "hinglish_b_final"):
        y, _, _, p2, s2, t2 = cache[k]
        var = fusion_variants(t2, p2)
        assert np.allclose(np.round(var["full"], 4), s2, atol=1e-4), "fusion re-implementation drifted from ThreatScorer"
        X5[k] = {name: {kk: Scores(y, v).metrics(boot=0)[kk] for kk in ("f1", "precision", "recall", "fpr")} for name, v in var.items()}
    R["X5_fusion_ablation"] = X5

    # X6 -----------------------------------------------------------------------------------
    X6 = {}
    extra = {}
    b = load_cross_b()
    if b is not None:
        extra["cross_domain_dataset_b"] = b
    for k, d in {**tests, **extra}.items():
        y = lab(d)
        link = np.array([1.0 if _URL.search(t) else 0.0 for t in d.text.astype(str)])
        lp = np.array([1.0 if (_URL.search(t) or _PHONE.search(t)) else 0.0 for t in d.text.astype(str)])
        row = {"has_link": summary(Scores(y, link).metrics(boot=0)), "has_link_or_phone": summary(Scores(y, lp).metrics(boot=0))}
        if k in cache:
            row["scamguard_v2"] = summary(Scores(y, cache[k][4]).metrics(boot=0))
        else:
            row["scamguard_v2_note"] = "not scored: ScamGuard-IN-2026 contains India SMS rows, so it would leak"
        # where links are absent: recall on scams with no link
        nolink = (link == 0) & (y == 1)
        if nolink.any() and k in cache:
            row["scams_without_link"] = {"n": int(nolink.sum()), "recall_has_link_rule": 0.0, "recall_scamguard_v2": float((cache[k][4][nolink] >= 0.5).mean())}
        X6[k] = row
    R["X6_rule_baselines"] = X6

    # X7 -----------------------------------------------------------------------------------
    sample = tests["real_test"].text.astype(str).tolist()[:500]
    v2.score(sample[:20])
    t1 = time.perf_counter()
    v2.score(sample)
    R["X7_latency"] = {"messages": len(sample), "ms_per_message_cpu": (time.perf_counter() - t1) * 1000 / len(sample), "cpus": os.cpu_count()}

    R["runtime_seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(HERE, "results_v2.json"), "w") as fh:
        json.dump(R, fh, indent=1)
    write_md(R)
    print("done in", R["runtime_seconds"], "s")
    return 0


def f(x, n=3):
    return f"{100 * x:.1f}" if isinstance(x, float) else str(x)


def write_md(R: dict) -> None:
    L = ["# ScamGuard v2 results", "", "Generated by `python -m ml_training.research.v2_experiments`. Do not edit by hand.", "",
         "Percentages. F1/FPR are of the final verdict (classifier + risk engine) unless marked. 95% bootstrap CIs in brackets.", "",
         "## X1. v1 vs v2", "", "v1 reported = exam model scored on raw text (as in the v1 report). v1 deployed = the same model as the live v1 app scored it. McNemar compares v1 deployed with v2.", "",
         "| Test set | n | v1 reported F1 | v1 reported FPR | v1 deployed F1 | v1 deployed FPR | v2 F1 | v2 FPR | McNemar p |", "|---|---|---|---|---|---|---|---|---|"]
    for k, v in R["X1_main"].items():
        o, a, b = v["v1_reported"]["final"], v["v1"]["final"], v["v2"]["final"]
        ci = lambda m: f" [{f(m['f1_ci'][0])}-{f(m['f1_ci'][1])}]" if "f1_ci" in m else ""
        L.append(f"| {k} | {a['n']} | {f(o['f1'])} | {f(o['fpr'])} | {f(a['f1'])}{ci(a)} | {f(a['fpr'])} | {f(b['f1'])}{ci(b)} | {f(b['fpr'])} | {v['mcnemar_final_v1_vs_v2']['p_value']:.3g} |")
    for k, v in R["X1_main"].items():
        if "per_template" in v:
            pt = v["per_template"]
            L.append(f"\n{k}: {pt['templates']} templates; mostly right: v1 {pt['v1_templates_mostly_right']}, v2 {pt['v2_templates_mostly_right']}. "
                     f"v2 failed templates: {', '.join(x['template'] + ' (' + x['label'] + ')' for x in pt['v2_failed_templates']) or 'none'}")
    L += ["", "## X2. Adversarial robustness (real test set, attacked)", "", "| Attack | messages changed | v1 recall | v1 FPR | v2 recall | v2 FPR |", "|---|---|---|---|---|---|"]
    for k, v in R["X2_adversarial"].items():
        L.append(f"| {k} | {f(v['messages_changed']) if 'messages_changed' in v else '-'} | {f(v['v1']['recall'])} | {f(v['v1']['fpr'])} | {f(v['v2']['recall'])} | {f(v['v2']['fpr'])} |")
    x3 = R["X3_temporal"]
    L += ["", "## X3. Temporal drift", "", f"Dated campaigns: {x3['dated_campaigns']} (by first year: {x3['campaigns_by_first_year']}). "
          f"Train excludes 2021+ campaigns ({x3['train_rows']} rows); test = {x3['future_scam_messages']} scam messages from {x3['future_campaigns']} campaigns first seen in 2022-23.", "",
          "| Hold-out | scam recall | FPR on real genuine |", "|---|---|---|",
          f"| Future (2022-23) | {f(x3['temporal']['recall_future_scams'])} | {f(x3['temporal']['fpr_real_genuine'])} |"]
    for r in x3["random_holdout"]:
        L.append(f"| Random campaigns, seed {r['seed']} ({r['scam_messages']} msgs) | {f(r['recall'])} | {f(r['fpr_real_genuine'])} |")
    c = R["X4_calibration"]
    L += ["", "## X4. Calibration and review band (v2, real test)", "", f"ECE: classifier {c['ece_classifier']:.4f}, final {c['ece_final']:.4f}", "",
          "| Review band | flagged for review | errors inside | errors outside | accuracy outside |", "|---|---|---|---|---|"]
    for k, v in c["review_band"].items():
        L.append(f"| {k} | {f(v['share_flagged_for_review'])} | {v['errors_inside']} | {v['errors_outside']} | {f(v['accuracy_outside'])} |")
    L += ["", "## X5. Fusion ablation (v2)", ""]
    for k, v in R["X5_fusion_ablation"].items():
        L += [f"**{k}**", "", "| Variant | F1 | Precision | Recall | FPR |", "|---|---|---|---|---|"]
        L += [f"| {n} | {f(m['f1'])} | {f(m['precision'])} | {f(m['recall'])} | {f(m['fpr'])} |" for n, m in v.items()] + [""]
    L += ["## X6. Simple-rule baselines", "", "| Test set | has-link F1 | has-link FPR | link-or-phone F1 | ScamGuard v2 F1 | ScamGuard v2 FPR | scams without a link: v2 recall |", "|---|---|---|---|---|---|---|"]
    for k, v in R["X6_rule_baselines"].items():
        nl = v.get("scams_without_link")
        L.append(f"| {k} | {f(v['has_link']['f1'])} | {f(v['has_link']['fpr'])} | {f(v['has_link_or_phone']['f1'])} | {f(v['scamguard_v2']['f1']) if 'scamguard_v2' in v else 'n/a (leak)'} | {f(v['scamguard_v2']['fpr']) if 'scamguard_v2' in v else 'n/a'} | "
                 f"{(f(nl['recall_scamguard_v2']) + ' (n=' + str(nl['n']) + ')') if nl else '-'} |")
    x7 = R["X7_latency"]
    L += ["", "## X7. Latency", "", f"{x7['ms_per_message_cpu']:.2f} ms per message, full deployed path, {x7['cpus']} CPU cores.", ""]
    with open(os.path.join(HERE, "results_v2.md"), "w") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
