# Cross-Domain Generalization and Lightweight Domain Adaptation for SMS Spam Detection

Does an SMS spam classifier trained on UK messages (UCI SMS Spam Collection) work on Indian SMS, and
does adding a small labelled Indian sample to training fix it?

## Folder contents

| Path | What it is |
|---|---|
| `CrossDomain_SMS_Spam.ipynb` | The full experiment notebook, already executed, with all outputs |
| `notebook_src.py` | The same notebook as a plain Python script (jupytext percent format) |
| `data/raw/` | Dataset A (`SMSSpamCollection`, UCI, CC BY 4.0) and Dataset B (`spam_ham_india.csv`, MIT) with B's README and licence |
| `data/clean/` | Both datasets after cleaning |
| `outputs/tables/` | Every result table as CSV (`table1` … `table9`, guide numbering) |
| `outputs/figures/` | All charts (PNG) |
| `outputs/models/` | Saved baseline and adapted models (joblib) used by the app |
| `outputs/results.json` | All results in one file |
| `outputs/tables/error_annotation_template.csv` | Misclassified messages with a blank `manual_category` column to fill in by hand |
| `app/` | Streamlit app and its `requirements.txt` |

## Run the notebook

**Google Colab:** upload `CrossDomain_SMS_Spam.ipynb`, then Runtime → Run all. It downloads both
datasets itself. **Locally:** `pip install pandas numpy scikit-learn==1.7.2 scipy matplotlib joblib ftfy datasketch jupyter`
and run the notebook from this folder (it uses the files in `data/raw`). A full run takes about one minute on a laptop CPU.

## Run the app

```
pip install -r app/requirements.txt
streamlit run app/app.py
```

## Protocol in one paragraph

Both datasets get the same light cleaning (label mapping, encoding repair, lowercase, whitespace,
exact-duplicate removal; URLs, numbers and punctuation kept), and the one message shared by A and B is
removed from B. Hyperparameters are chosen by 5-fold cross-validation on Dataset A training data only.
Dataset A is split 80/20 and Dataset B 70/30 (adaptation pool / final target test), both stratified.
Adaptation adds 0%, 10%, 20% or 40% of the pool to A's training data and refits TF-IDF and the
classifier; every setting is scored on the same untouched final target test. Everything is repeated
with seeds 42, 123 and 2026 (mean ± SD), and paired with McNemar's test.
