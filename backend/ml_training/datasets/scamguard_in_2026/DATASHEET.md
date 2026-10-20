# ScamGuard-IN-2026: datasheet

A labelled corpus of Indian SMS for scam-vs-genuine classification, built for the
ScamGuard project (BMS College of Engineering). It replaces the 2011 UK SMS Spam
Collection used by model v3, which has been removed from the project.

Build it with `python -m ml_training.datasets.scamguard_in_2026.build` (needs the raw
sources, see `fetch_sources.sh`). The build is deterministic: the same sources give a
byte-identical `scamguard_in_2026.csv`.

## Why a new dataset

* The UCI SMS Spam Collection (2011, UK) labels premium-rate promotions as spam. It has no
  KYC, UPI, digital-arrest, e-challan or task scams, no Indian bank alerts and no Hindi.
* Public Indian "scam/ham" sets on Hugging Face are synthetic with undocumented
  generation; the India Spam SMS set labels brand promotions as spam, not scams.
* No public, labelled, real 2025-26 Indian scam *and* genuine SMS corpus exists (checked
  October 2026). So the corpus combines real reported scams, real genuine messages,
  team-contributed 2026 messages and clearly marked synthetic messages, and evaluates
  only on real messages.

## Sources

| Id | Source | Licence | What is used | Role |
|---|---|---|---|---|
| R1 | IMC'25 smishing corpus (Agarwal, Papasavva, Suarez-Tangil, Vasek, ACM IMC 2025), 33,869 user-reported SMS | CC BY 4.0 | India-relevant English/Hindi messages, audited (see below) | train / dev / test |
| R2 | India Spam SMS collection (junioralive, GitHub/Kaggle), 2,267 Indian SMS | MIT | "ham" kept as genuine; brand promotions relabelled genuine after audit | train / dev / test |
| R3 | Scam texts quoted in 2025-26 advisories and news, plus one genuine 2026 notice | quoted for research | 12 messages, source URL and date per row (`advisories_2025_26.csv`) | test only |
| R4 | SMS contributed by the project team in 2026, PII-masked (`pii.py`) | team consent | genuine and scam messages received in 2025-26 | test only |
| S | Synthetic templates (`synthetic.py`) covering 2025-26 scam types and genuine Indian formats | project | 4,737 messages | train only |

Raw files live in `raw/` and are not committed; team raw files (`raw/team/`) never leave
the machine they were masked on. Only masked, reviewed text is stored (`team_2026.csv`).

## Labels

`scam` = the message tries to get money, a secret (OTP/PIN/CVV/password), personal
data, an install or a call to a private number by deception. `legitimate` = everything
else, including genuine promotions, bank alerts, OTPs with a warning, service notices and
personal chat. Promotions are not scams.

### Label audit (a main finding)

IMC'25 rows are messages users *reported* as smishing. Reporting is not the same as
being a scam: a random sample of 70 campaigns found about a third were genuine.
Every IMC campaign (4,077 near-duplicate groups) was therefore labelled:

1. **Rule-confirmed scam** (1,253 campaigns): strong fraud cue and no genuine cue
   (`relabel.py`; independent of the app's ThreatScorer). A 40-campaign check found no error.
2. **Manual review** (1,669 campaigns): every other campaign read and labelled scam /
   genuine / unclear-drop. Result: 583 scam, 867 genuine, 219 dropped.
3. **Second pass**: a cross-validated model flagged 44 rows whose label it strongly
   disagreed with; each was re-read (19 relabelled, 7 dropped, 18 kept).

Outcome: 950 IMC rows (19% of the subset) are genuine messages that users had reported.
`label_corrections.csv`, `imc_audit.csv` and `india_sms_audit.csv` record every decision.

## Splits

* Near-duplicates are grouped into **campaigns** (MinHash LSH, Jaccard >= 0.6 on word
  3-shingles after masking numbers and links). 4,085 real campaigns; the largest has 128 messages and the top 1% of campaigns hold 14% of real rows.
* Real data is split **by campaign** (hash of the campaign's first text): 25% test,
  15% dev, 60% train. No campaign appears in two splits. Synthetic data is train-only.
* `test_2026` holds R3 and R4 and is never used for training or tuning.
* The split was generated once more (salt `sg26-v2`) after a first error analysis on
  the original test split; since then, model and rule changes were analysed on **dev**
  only. The hand-written challenge sets in `tests/data` and `indian_challenge_set*.csv`
  were used while designing the intent rules, so they are development sets, not
  independent tests.

## Counts (current build)

| Split | Genuine | Scam |
|---|---|---|
| train | 4,581 | 4,064 |
| dev | 361 | 507 |
| test (real only) | 665 | 1,209 |
| test_2026 | 1 | 11 (team data pending) |

8,822 campaigns in total. Sources: IMC'25 963 genuine / 3,987 scam, India SMS 1,694 /
6, synthetic 2,950 / 1,787, advisories 1 / 11.

## Preprocessing

IMC'25 anonymises entities as `<URL>`, `<PHONE_NUMBER>`, `<DATE_TIME>` and so on. The
build replaces them with neutral surface forms (`http://link.example/x`, `9876543210`,
`12-05`) that the app's text cleaner maps to the same tokens as real links, numbers and
dates, so training text looks like what users paste. Team messages get the same treatment
from `pii.py` (OTPs, account numbers, phone numbers, UPI IDs, e-mails and names replaced).

## Known limitations

* IMC'25 messages are mostly 2022-2024. The 2025-26 scam types in training come from the
  synthetic templates; the only real 2025-26 evaluation is `test_2026`, which is small
  until the team data arrives.
* Labels reflect one careful reviewer per item, without a second annotator, so no
  inter-annotator agreement figure is available. Borderline messages (debt collection,
  aggressive loan ads, collect requests) were dropped rather than guessed.
* English and Hindi (Devanagari) only; other Indian languages are not covered.
* Synthetic text is cleaner than real text; that is why it is never in a test split.
