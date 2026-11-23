# ScamGuard v2: what changed and what it measured

v1 is the version examined on 23.11.2026 (git tag `v1.0-exam`). v2 adds Hindi and Hinglish support, resistance
to disguised words, a Telegram channel, and a fuller evaluation. Every number below is produced by
`python -m ml_training.research.v2_experiments` (from `backend/`, about 40 seconds on a laptop CPU) and is in
[results_v2.md](../../backend/ml_training/research/results_v2.md).

## Changes

| Area | v1 | v2 |
|---|---|---|
| Languages | English; a display-only Hindi/Hinglish concept list | English, Devanagari Hindi and Hinglish in the data and in the intent rules |
| Disguised words | not handled | `deobfuscate()`: lookalike Cyrillic/Greek letters, zero-width characters, spaced-out letters ("c l i c k"), leetspeak ("acc0unt"), defanged links ("hxxp", "[.]", "dot com"), full-width letters |
| Serving path | a "Detected concepts" summary was appended to the text before the model, which never saw it in training | summary kept for display only; model input = de-obfuscated text, the same as in training |
| Stored text | text plus the appended summary | exactly what the user entered |
| Model | logistic regression v4 | logistic regression v5 (same learner, + 1,200 synthetic Hinglish/Hindi training rows) |
| Channels | website, PWA, browser extension | + Telegram bot (webhook inside the backend, no extra server) |
| Evaluation | campaign split, challenge set, ablations, bootstrap CIs | + adversarial attacks, temporal split, calibration, review band, fusion ablation, rule baselines, McNemar tests, latency, transformer comparison (Colab) |

## Results

**Real test set** (1,874 messages, campaign-held-out). v1 "reported" is how the v1 report scored it (raw text);
v1 "deployed" is what the live v1 app actually did.

| System | Accuracy | F1 (95% CI) | False alarms |
|---|:---:|:---:|:---:|
| v1 reported | 97.1% | 97.7% (97.1-98.3) | 3.2% |
| v1 deployed | 96.3% | 97.1% (96.4-97.8) | 3.9% |
| **v2** | **96.7%** | **97.5% (96.8-98.0)** | **3.9%** |

v2 vs v1 deployed: McNemar p = 0.12, so on English the two are not significantly different. v2's gains are on
disguised and Hindi/Hinglish messages:

| Test | v1 deployed | v2 |
|---|:---:|:---:|
| Evasion attack, all tricks combined: scams caught | 88.4% | 97.2% |
| Single tricks (lookalike, zero-width, spaced, leetspeak, defanged link): scams caught | 94.0-96.0% | 96.9-97.2% |
| Hinglish/Hindi set B (final, 300 msgs, 36 templates): F1 / false alarms | 85.0% / 12.7% | 100% / 0% |
| Hinglish/Hindi set A (used for error analysis): F1 / false alarms | 88.8% / 9.3% | 95.5% / 9.3% |
| Challenge set (259, hand-written hard cases): F1 | 96.9% | 96.0% |
| **Real Hindi messages** (77 unused IMC'25 reports, 60 groups): F1 / false alarms | 63.9% / 33.3% | 66.7% / 26.2% (McNemar p = 0.38) |

**The real Hindi result is the most important number in this document.** The 77 messages are the IMC'25 Hindi
reports that were not in the dataset, labelled by the dataset rule before any model scored them (50 chat fragments,
promotions and unclear reports were dropped, not guessed). v2's 100% on synthetic set B does not carry over: real
lures ("PM loan yojana, 1% interest, call ...", "Amazon sale, camera for Rs 199") are missing from the templates,
and genuine Devanagari notices (Covid test results, Airtel recharge reminders) are flagged because most Devanagari
text the model has seen is a scam. The set was not used to tune anything. Fixing this needs real labelled Hindi
messages and a model pre-trained on Hindi (MuRIL), which the transformer notebook tests on this set.

Real scam messages already use these tricks: the real test set contains "Y0N0" (zeros for O) and "H.D.F.C".

**Other findings**

- **Temporal split.** Trained on campaigns first seen up to 2020, the model caught 99.6% of 855 scam messages
  from campaigns first seen in 2022-23, versus 95.4-99.0% for random hold-outs of the same size. No drift was
  visible, but many training campaigns have no date, so this is a weak test.
- **Calibration.** Expected calibration error 0.008 for the classifier and 0.017 for the final score. Flagging
  scores between 0.3 and 0.7 as "check before you act" covers 3.6% of messages and a third of all errors (20 of 61).
- **Fusion ablation.** On the English test set the classifier alone is better (98.1% F1, 2.7% false alarms) than
  classifier + rules (97.5%, 3.9%). The rules pay for themselves out of distribution: +5.8 F1 on the challenge set
  and +8.7 F1 on Hinglish set B, at 0% false alarms on both. This trade-off is kept on purpose.
- **Simple rules are not enough.** "Has a link" scores 56.2% F1 with 36.1% false alarms on the real test set and
  misses all 642 scams that contain no link; ScamGuard catches 95.8% of those. (The same rule scores 94.1% on the
  cross-domain India SMS set, which says more about that dataset than about the rule.)
- **Speed.** 0.67 ms per message for the full path on 2 CPU cores.

## Transformers (MuRIL, XLM-R), Colab T4, one seed

`research/transformer/ScamGuard_Transformers_Colab.ipynb` runs `transformer_experiment.py`: 3 epochs on the v2
training split, epoch chosen on dev, same de-obfuscated text. LR is retrained on the same split for a like-for-like
comparison. Full tables: [transformer_results.md](../../backend/ml_training/research/transformer_results.md).

| Test (F1 / false alarms) | LR v2 | MuRIL | XLM-R |
|---|:---:|:---:|:---:|
| Real English test | 97.1 / 4.5% | 97.5 / 2.6% | 97.8 / 3.2% |
| **Real Hindi (77)** | 64.7 / 26.2% | 69.2 / 38.1% | **88.9 / 11.9%** (McNemar p = 0.0001) |
| Synthetic Hinglish B | 100 / 0% | 92.9 / 11.3% | 84.5 / 32.0% |
| UCI-trained, tested on India SMS | 67.8 | 97.5 | 95.8 |

- **XLM-R fixes most of the real-Hindi weakness:** it corrects 17 of LR's errors and introduces 1.
- **The synthetic Hinglish set ranks the systems the wrong way round.** It rewards the hand-written rules, which
  confirms that synthetic templates measure coverage, not accuracy.
- **Pre-training removes most of the cross-domain gap** that the v1 study fixed with local data.
- **These are single-seed runs** on a small real-Hindi set. The next step is to route Hindi/Hinglish messages to
  XLM-R once a GPU or larger server is available.

## How the Hinglish/Hindi sets were made (and why they are not real-world data)

The generator (`ml_training/datasets/scamguard_in_2026/hinglish.py`) has three template banks written separately:
TRAIN (80% of its templates train, 20% dev), TEST A and TEST B. Settings were chosen on the dev split and the dev
templates only. Set A was looked at once for error analysis, so it is reported as a development check; set B was
written afterwards and scored only in the final run. Exact-text overlap between training and both test sets is 0.
All three banks and the Hindi/Hinglish rules were written by the same team, so set B shows the system covers these
kinds of phrasing; it does not measure accuracy on real traffic. The real-Hindi result above shows the gap.

## Not done yet (and not claimed)

- **Transformers in production.** XLM-R fixes most of the real-Hindi gap (below), but at about 1 GB it does not fit the
  free CPU server, so the deployed model is still LR v5.
- **User pilot.** `docs/v2/PILOT_KIT.md` and `backend/scripts/sus_score.py` are ready; no pilot has been run.
- **Human-labelled agreement (kappa).** Not done; the label audit from v1 still applies.
- **Paper.** The v1 paper is submitted to COMP-SIF 2027 (Paper ID 1206) and under review.
