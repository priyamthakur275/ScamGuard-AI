"""Build ScamGuard-IN-2026 from its sources.

    python -m ml_training.datasets.scamguard_in_2026.build

Sources (see DATASHEET.md for licences and details):
  R1  IMC'25 smishing corpus (real scam SMS reported by users; CC BY 4.0) - India-relevant subset
  R2  India Spam SMS collection (real Indian SMS; MIT) - "ham" kept as genuine; brand promotions
      relabelled genuine-promotional; promotions with fraud cues dropped (not relabelled)
  R3  2025-26 advisory set: scam texts quoted in public advisories and news (test only)
  R4  Team-contributed 2026 SMS, PII-masked (raw files never committed; test only)
  S   Synthetic templates (synthetic.py), training only

Output: scamguard_in_2026.csv with columns
  text, label, source, subtype, is_synthetic, campaign, split
where ``campaign`` groups near-duplicate messages (MinHash, Jaccard >= 0.6 on word
3-shingles) and ``split`` is train / dev / test / test_2026. Real data is split by
campaign, so no scam campaign appears in both train and test.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import html
import os
import re
import xml.etree.ElementTree as ET

import pandas as pd
from datasketch import MinHash, MinHashLSH

from ml_training.datasets.scamguard_in_2026 import synthetic
from ml_training.datasets.scamguard_in_2026.pii import mask_pii

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "scamguard_in_2026.csv")
STATS = os.path.join(HERE, "build_stats.txt")

N_SYN_GENUINE = 3000
N_SYN_SCAM = 1800
TEST_FRACTION = 0.25

INDIA = re.compile(
    r"(?i)\b(SBI|HDFC|ICICI|Axis|Kotak|PNB|Canara|Paytm|PhonePe|UPI|Aadhaar|Aadhar|PAN ?card|KYC|Rs\.?|INR|₹|India ?Post|"
    r"electricity|bijli|Jio|Airtel|BSNL|Vodafone|YONO|IRCTC|Flipkart|lakh|crore|rupees|TRAI|RBI|income tax|EPFO|PM ?Kisan|"
    r"challan|FASTag|Indane|Meesho|Snapdeal|BESCOM|consumer)\b")

# IMC'25 rows that are not scams: genuine verification codes and plain brand ads that users reported as spam.
IMC_NOT_SCAM = re.compile(
    r"(?i)(google is (re-?)?verifying the phone|^\W*\(?[a-z0-9]{8,14}\)?\s*google|"
    r"^\s*(please )?enter (your )?otp \d+ to verify|^\s*\d{4,8} is your (otp|verification code|code)\b(?!.*\b(share|send|tell|forward)\b))")

PLACEHOLDERS = [
    (re.compile(r"<URL>ease"), "please"),
    (re.compile(r"<URL>"), " http://link.example/x "),
    (re.compile(r"<(PHONE_NUMBER|US_BANK_NUMBER|UK_NHS|US_DRIVER_LICENSE|US_PASSPORT|US_SSN|MEDICAL_LICENSE|IBAN_CODE|CREDIT_CARD|IP_ADDRESS)>"), " 9876543210 "),
    (re.compile(r"<DATE_TIME>"), " 12-05 "),
    (re.compile(r"<EMAIL_ADDRESS>"), " user@mail.example "),
    (re.compile(r"<[A-Z_]+>"), " "),
]

FRAUD_CUES = re.compile(r"(?i)\b(kyc|blocked|suspend\w*|won|winner|lottery|prize|loan|wallet|lakh|job|earn\w*|apk|otp|verify|pin|cvv|lucky)\b")


def restore_placeholders(t: str) -> str:
    for rx, rep in PLACEHOLDERS:
        t = rx.sub(rep, t)
    return re.sub(r"[ \t]+", " ", t).strip()


def norm_key(t: str) -> str:
    t = re.sub(r"https?://\S+|\S+\.(com|in|ly|me|xyz|top|co|link|example)\S*", " url ", t.lower())
    t = re.sub(r"\d+", "0", t)
    return re.sub(r"[^a-z0ऀ-ॿ ]+", " ", t).strip()


def shingles(t: str) -> set[str]:
    w = norm_key(t).split()
    if len(w) < 3:
        return {" ".join(w)}
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}


def campaigns(texts: list[str], prefix: str) -> list[str]:
    lsh = MinHashLSH(threshold=0.6, num_perm=96)
    out: list[str] = []
    rep: dict[str, str] = {}
    for i, t in enumerate(texts):
        h = MinHash(num_perm=96)
        for s in shingles(t):
            h.update(s.encode())
        hit = lsh.query(h)
        key = f"{prefix}{i:06d}"
        if hit:
            out.append(rep[min(hit)])  # LSH returns an unordered list; take the earliest campaign so builds are reproducible
        else:
            lsh.insert(key, h)
            rep[key] = key
            out.append(key)
    return out


SPLIT_SALT = "sg26-v2"  # the split was regenerated once, after the first error analysis (see DATASHEET.md)
DEV_FRACTION = 0.15


def split_of(campaign: str, text: str) -> str:
    # Hash the campaign's first text, not its id, so the split does not move when rows are added.
    v = int(hashlib.sha1((SPLIT_SALT + norm_key(text)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    if v < TEST_FRACTION:
        return "test"
    return "dev" if v < TEST_FRACTION + DEV_FRACTION else "train"


def load_imc(stats: list[str]) -> pd.DataFrame:
    d = pd.read_csv(os.path.join(RAW, "imc25_smishing.csv"))
    d["text"] = d["text"].astype(str)
    m = ((d.original_network_country == "IND") | d.text.str.contains(INDIA)) & d.language.isin(["English", "Hindi"])
    d = d[m & ~d.scam_type.isin(["spam"])].copy()
    stats.append(f"R1 IMC'25 India-relevant English/Hindi, excluding 'spam' category: {len(d)}")
    noise = d.text.str.contains(IMC_NOT_SCAM)
    stats.append(f"R1 removed as label noise (genuine verification codes): {int(noise.sum())}")
    d = d[~noise]
    d["text"] = d.text.map(restore_placeholders)
    d = d[d.text.str.len() >= 15]
    d = d.drop_duplicates("text")
    stats.append(f"R1 after placeholder restore, length>=15, exact dedupe: {len(d)}")
    return pd.DataFrame({"text": d.text, "label": "scam", "source": "imc25", "subtype": d.scam_type.fillna("others"), "is_synthetic": 0})


def apply_imc_audit(real: pd.DataFrame, stats: list[str]) -> pd.DataFrame:
    """Relabel IMC'25 rows from imc_audit.csv (one decision per campaign: rule-confirmed
    scam, or a manual decision scam / legitimate / drop). See relabel.py."""
    audit = pd.read_csv(os.path.join(HERE, "imc_audit.csv"))
    by_key = dict(zip(audit.key, audit.label))
    imc = real.source == "imc25"
    keys = real.text.map(norm_key)
    row_label = keys.map(by_key)
    camp_label = row_label[imc].groupby(real.campaign[imc]).first()
    label = real.campaign.map(camp_label).where(row_label.isna(), row_label)
    label = label.where(imc, real.label)
    from ml_training.datasets.scamguard_in_2026.relabel import classify
    unseen = imc & label.isna()
    label[unseen] = real.text[unseen].map(lambda t: {"scam": "scam", "genuine": "legitimate"}.get(classify(t), "drop"))
    # India SMS promotions: the manual audit found a few scams among the "promotions".
    pa = pd.read_csv(os.path.join(HERE, "india_sms_audit.csv"))
    promo = (real.source == "india_sms") & (real.subtype == "brand_promotion")
    p_row = keys.map(dict(zip(pa.key, pa.label)))
    p_camp = p_row[promo].groupby(real.campaign[promo]).first().dropna()
    p_label = real.campaign.map(p_camp).where(p_row.isna(), p_row)
    label = label.where(~(promo & p_label.notna()), p_label)
    stats.append(f"R2 promotion audit: moved to scam {int((promo & (p_label == 'scam')).sum())}, dropped {int((promo & (p_label == 'drop')).sum())} (rows)")
    real = real.assign(label=label)
    real.loc[promo & (real.label == "scam"), "subtype"] = "promo_was_scam"
    moved = imc & (real.label == "legitimate")
    real.loc[moved, "subtype"] = "reported_but_genuine"
    stats.append(f"R1 audit: scam {int((imc & (real.label == 'scam')).sum())}, relabelled genuine {int(moved.sum())}, "
                 f"dropped as unclear {int((imc & (real.label == 'drop')).sum())} (rows); unseen-by-audit {int(unseen.sum())}")
    return real[real.label != "drop"]


def load_india_sms(stats: list[str]) -> pd.DataFrame:
    d = pd.read_csv(os.path.join(RAW, "india_spam_sms.csv"), encoding="latin-1").dropna()
    d.columns = ["text", "label"]
    d["text"] = d.text.astype(str).map(lambda s: html.unescape(s).strip())
    d = d[(d.text.str.len() >= 8) & ~d.text.str.contains(r"\?{4,}|Ã")]  # drop rows broken by encoding
    ham = d[d.label == "ham"]
    promo = d[d.label == "spam"]
    cue = promo.text.str.contains(FRAUD_CUES)
    stats.append(f"R2 India SMS: genuine 'ham' kept {len(ham)}; promotions relabelled genuine {int((~cue).sum())}; promotions with fraud cues dropped {int(cue.sum())}")
    rows = [pd.DataFrame({"text": ham.text, "label": "legitimate", "source": "india_sms", "subtype": "personal_or_work", "is_synthetic": 0}),
            pd.DataFrame({"text": promo[~cue].text, "label": "legitimate", "source": "india_sms", "subtype": "brand_promotion", "is_synthetic": 0})]
    return pd.concat(rows).drop_duplicates("text")


def load_advisories(stats: list[str]) -> pd.DataFrame:
    p = os.path.join(HERE, "advisories_2025_26.csv")
    if not os.path.exists(p):
        return pd.DataFrame(columns=["text", "label", "source", "subtype", "is_synthetic"])
    d = pd.read_csv(p)
    stats.append(f"R3 2025-26 advisory set: {len(d)} ({d.label.value_counts().to_dict()})")
    return pd.DataFrame({"text": d.text, "label": d.label, "source": "advisory_2025_26", "subtype": d.subtype, "is_synthetic": 0})


def _team_messages() -> list[tuple[str, str]]:
    """(text, label hint) from raw/team/: SMS Backup & Restore XML, or .txt (one message per line).
    A file whose name contains 'scam' is scam; otherwise genuine. Every row is reviewed via team_review.csv."""
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, "team", "*"))):
        hint = "scam" if "scam" in os.path.basename(f).lower() else "legitimate"
        if f.lower().endswith(".xml"):
            for el in ET.parse(f).getroot().iter("sms"):
                if el.get("type") == "1" and el.get("body"):  # received only
                    out.append((el.get("body"), hint))
        elif f.lower().endswith((".txt", ".csv")):
            with open(f, encoding="utf-8", errors="replace") as fh:
                out += [(ln.strip(), hint) for ln in fh if len(ln.strip()) >= 8]
    return out


def load_team(stats: list[str]) -> pd.DataFrame:
    review = os.path.join(HERE, "team_2026.csv")  # masked and reviewed; this file is committed
    msgs = _team_messages()
    if msgs:
        rows = [{"text": mask_pii(t), "label": h} for t, h in msgs]
        new = pd.DataFrame(rows).drop_duplicates("text")
        if os.path.exists(review):
            new = pd.concat([pd.read_csv(review)[["text", "label"]], new]).drop_duplicates("text", keep="first")
        new.to_csv(review, index=False, quoting=csv.QUOTE_MINIMAL)
    if not os.path.exists(review):
        stats.append("R4 team 2026 SMS: not yet provided")
        return pd.DataFrame(columns=["text", "label", "source", "subtype", "is_synthetic"])
    d = pd.read_csv(review)
    d = d[d.label.isin(["scam", "legitimate"])]
    stats.append(f"R4 team 2026 SMS (masked, reviewed): {len(d)} ({d.label.value_counts().to_dict()})")
    return pd.DataFrame({"text": d.text, "label": d.label, "source": "team_2026", "subtype": "team", "is_synthetic": 0})


def build() -> pd.DataFrame:
    stats: list[str] = []
    real = pd.concat([load_imc(stats), load_india_sms(stats)], ignore_index=True)
    real["campaign"] = campaigns(real.text.tolist(), "c")
    real = apply_imc_audit(real, stats)
    first = real.groupby("campaign").text.first()
    real["split"] = real.campaign.map({c: split_of(c, t) for c, t in first.items()})
    stats.append(f"Real R1+R2 unique campaigns: {real.campaign.nunique()} from {len(real)} rows")

    later = pd.concat([load_advisories(stats), load_team(stats)], ignore_index=True)
    later["campaign"] = [f"t{i}" for i in range(len(later))]
    later["split"] = "test_2026"

    syn = pd.DataFrame(synthetic.generate(N_SYN_GENUINE, N_SYN_SCAM))
    syn["source"], syn["is_synthetic"], syn["split"] = "synthetic", 1, "train"
    syn["campaign"] = [f"s{i}" for i in range(len(syn))]
    stats.append(f"S synthetic (train only): {len(syn)} ({syn.label.value_counts().to_dict()})")

    df = pd.concat([real, later, syn], ignore_index=True)
    df["text"] = df.text.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    # A message text may appear in only one split; real rows win over synthetic ones.
    df = df.drop_duplicates("text", keep="first")
    keyed = df.assign(k=df.text.map(norm_key))
    test_keys = set(keyed[keyed.split != "train"].k)
    leak = (keyed.split == "train") & keyed.k.isin(test_keys)
    stats.append(f"Train rows dropped because a near-identical text is in a test split: {int(leak.sum())}")
    df = df[~leak.values]
    # Second-pass label review (rows where a cross-validated model strongly disagreed with the label).
    corr = pd.read_csv(os.path.join(HERE, "label_corrections.csv"))
    fix = df.text.map(norm_key).map(dict(zip(corr.key, corr.label)))
    stats.append(f"Second-pass corrections: relabelled {int((fix.notna() & (fix != 'drop') & (fix != df.label)).sum())}, dropped {int((fix == 'drop').sum())} (rows)")
    df = df.assign(label=fix.where(fix.notna(), df.label))
    df = df[df.label != "drop"]
    df = df[["text", "label", "source", "subtype", "is_synthetic", "campaign", "split"]]
    df.to_csv(OUT, index=False)

    tab = df.groupby(["split", "source", "label"]).size().to_string()
    stats.append("\nRows by split / source / label:\n" + tab)
    with open(STATS, "w") as fh:
        fh.write("\n".join(stats) + "\n")
    print("\n".join(stats))
    return df


if __name__ == "__main__":
    build()
