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
