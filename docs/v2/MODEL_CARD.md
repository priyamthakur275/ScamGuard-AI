# Model card: ScamGuard logistic_regression v5

## Overview

| | |
|---|---|
| Task | Binary classification of a short message (SMS, WhatsApp, email text, OCR'd screenshot) as scam or genuine |
| Model | Logistic regression (C = 16, balanced class weights) on word 1-2-gram TF-IDF (30k) + character 2-5-gram TF-IDF (60k); 36,641 features |
| Final verdict | Model probability fused with an intent-based risk engine in log-odds space (`ml_service/inference/threat_scorer.py`); scam if the final score is at least 0.5 |
| Input processing | `deobfuscate()` (evasion-trick removal), then lowercase and placeholder tokens for URLs, phone numbers, numbers and emails |
| Languages | English, Hindi (Devanagari), Hinglish (Hindi in Latin script) |
| Training data | ScamGuard-IN-2026 train + dev (9,513 rows, of which 4,737 synthetic) + 1,200 synthetic Hinglish/Hindi rows |
| Artifacts | `backend/artifacts/logistic_regression/v5/`, registered in `artifacts/registry_index.json` |
| Reproduce | `python -m ml_training.research.train_production` (from `backend/`) |

## Intended use

Helping people in India decide whether a message is a scam before they click, pay, call back or share a code, with
an explanation of the warning signs and the official reporting channels (1930, cybercrime.gov.in, Chakshu). It is
an aid, not an authority: users should still verify through the official number of the bank or company.

**Not intended for:** blocking messages automatically without a human, judging people, or languages other than
English, Hindi and Hinglish.

## Evaluation

Real test set: 1,874 real Indian messages from scam campaigns held out of training (campaign-aware split).

| Accuracy | Precision | Recall | F1 (95% CI) | False alarms | ROC-AUC |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 96.7% | 97.8% | 97.1% | 97.5% (96.8-98.0) | 3.9% | 0.994 |

Other sets: challenge set (259 hard cases) 96.0% F1, 0% false alarms; Hinglish/Hindi set B (synthetic) 100% F1;
recall under a combined evasion attack 97.2%. Full results: `backend/ml_training/research/results_v2.md`.

## Known limitations

- About half the English training rows and all Hindi/Hinglish rows are synthetic; synthetic rows are never in the
  real test set, but real-world Hindi/Hinglish accuracy has not been measured.
- Genuine-message coverage is thinner than scam coverage; about 4 in 100 genuine messages are flagged.
- The risk engine's rules raise false alarms on English slightly (classifier alone: 2.7%) in exchange for much
  better recall on unfamiliar and code-mixed scams.
- Text only. Screenshots and PDFs depend on OCR quality; voice depends on transcription.
- Scam scripts change; the temporal test showed no drift on 2022-23 campaigns, but most training campaigns are undated.

## Privacy

The no-login quick check and the Telegram bot never store the message. Signed-in scans are stored in the user's
own history. Personal data in the dataset is masked (`pii.py`).
