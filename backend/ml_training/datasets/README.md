# Training datasets

| File | Rows | Source |
|---|---|---|
| `sms_spam_collection.csv` | 5,569 (747 spam, 4,822 legitimate) | SMS Spam Collection v.1, T. A. Almeida and J. M. Gómez Hidalgo — Kaggle: https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset (also UCI ML Repository). Licensed CC BY 4.0. |
| `sample_messages.csv` | 24 (12 scam, 12 legitimate) | Hand-written project samples |

Preparation of `sms_spam_collection.csv`: the original `ham` label was renamed to `legitimate`
(the validator's label set), and 5 messages shorter than 3 characters were dropped. The text
itself is unchanged. The loader removes exact duplicates when merging, leaving 5,193 unique rows.

Train the production model (v2) with:

```bash
cd backend
python -m ml_training.run_training \
  --dataset ml_training/datasets/sms_spam_collection.csv \
  --dataset ml_training/datasets/sample_messages.csv \
  --version v2 --artifacts-dir artifacts
```

Citation: T. A. Almeida, J. M. G. Hidalgo and A. Yamakami, "Contributions to the study of SMS
spam filtering: new collection and results," Proc. ACM DocEng, 2011.

## Indian scam supplement (model v3)

The SMS Spam Collection is UK spam from 2011 (prizes, ringtones). On Indian
scams it scored KYC/OTP fraud, fake job offers and digital-arrest calls at
5-20%, so v3 adds `indian_scam_supplement.csv`.

- **What it is:** 1,140 messages (520 scam, 620 genuine) composed by
  `build_indian_supplement.py` from fragments the team wrote by hand,
  modelled on fraud patterns in public advisories (RBI, CERT-In,
  I4C/cybercrime.gov.in, TRAI). Genuine messages deliberately reuse the same
  words (OTP, bank, KYC, bill, delivery) so the model learns intent, not topic.
- **What it is not:** field-collected data. Treat it as a curated supplement.

Training: `python -m ml_training.run_training --dataset ml_training/datasets/sms_spam_collection.csv --dataset ml_training/datasets/indian_scam_supplement.csv --version v3`
(SVM won: accuracy 0.989, precision 0.970, recall 0.970, F1 0.970 on the 20% split).

### Honest evaluation on messages never used for training

`indian_challenge_set.csv` (60) and `indian_challenge_set_b.csv` (40) were
written separately, share no fragments with the supplement, and are never
trained on. Set A was used while designing the intent rules; **set B was
written afterwards and scored once, so it is the number to quote.**

| Final verdict (model + intent engine) | Set A | Set B (unseen) |
|---|---|---|
| Before (v2 + keyword scorer) | 73.3% acc, 15 false alarms | 62.5% acc, 12 false alarms |
| After (v3 + intent scorer) | 96.7% acc, 1 false alarm | **87.5% acc, precision 0.895, recall 0.85, 2 false alarms** |

Run `python -m ml_training.evaluation.challenge_eval --show` to reproduce.
Known misses on set B: a pension "send a photo of your card" request, an
"accidentally transferred, send it back" message, and a custody/bail call.
No text classifier is 100% accurate; the app always shows its evidence so a
user can see why a message was flagged.
