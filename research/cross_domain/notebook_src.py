# %% [markdown]
# # Cross-Domain Generalization and Lightweight Domain Adaptation for SMS Spam Detection
#
# **Research question.** Does an SMS spam classifier trained on one dataset (UCI SMS Spam Collection,
# UK messages) still work on an independently collected dataset (Indian SMS), and does adding a small
# number of labelled Indian messages to training help?
#
# | Name | Role |
# |---|---|
# | Dataset A: UCI SMS Spam Collection | Source domain: the model learns here |
# | Dataset B: India Spam SMS Classification | Target domain: the model is tested here |
#
# The notebook follows the guide's stages in order. Every number printed below is produced by the code
# in this notebook; nothing is typed by hand.
#
# **Run it in Google Colab:** Runtime → Run all. It downloads both datasets itself.

# %% [markdown]
# ## 0. Setup
# Fixed seeds make every run give the same numbers. `SEEDS` are the three repetitions the guide asks for.

# %%
import os, io, re, json, zipfile, urllib.request, warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, classification_report)
from scipy.stats import binomtest
from sklearn.metrics import f1_score as _f1  # noqa: F401
import joblib

try:
    import ftfy  # repairs text whose encoding was broken (mojibake)
except ImportError:
    os.system("pip -q install ftfy")
    import ftfy

warnings.filterwarnings("ignore")
pd.set_option("display.max_colwidth", 120)

MAIN_SEED = 42            # the guide's random_state
SEEDS = [42, 123, 2026]   # three repetitions for mean ± standard deviation
ADAPT_FRACTIONS = [0.0, 0.10, 0.20, 0.40]   # share of the target adaptation pool added to training
REFERENCE_FRACTION = 1.0  # extra reference row: the whole pool (not part of the guide's protocol)

DATA_DIR = "data/raw"
OUT = "outputs"
for d in (DATA_DIR, OUT, f"{OUT}/figures", f"{OUT}/tables", f"{OUT}/models", "data/clean"):
    os.makedirs(d, exist_ok=True)

UCI_URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
INDIA_URL = ("https://raw.githubusercontent.com/junioralive/india-spam-sms-classification/"
             "main/dataset/spam_ham_india.csv")

print("Python libraries:", "pandas", pd.__version__, "| numpy", np.__version__,
      "| scikit-learn", sklearn.__version__, "| matplotlib", matplotlib.__version__)

# %% [markdown]
# ## 1. Load both datasets (guide Prompt 2)
# If the files are already in `data/raw` they are used; otherwise they are downloaded from the
# official UCI page and the dataset's GitHub repository.

# %%
uci_path = os.path.join(DATA_DIR, "SMSSpamCollection")
if not os.path.exists(uci_path):
    raw = urllib.request.urlopen(UCI_URL).read()
    zipfile.ZipFile(io.BytesIO(raw)).extract("SMSSpamCollection", DATA_DIR)

india_path = os.path.join(DATA_DIR, "spam_ham_india.csv")
if not os.path.exists(india_path):
    urllib.request.urlretrieve(INDIA_URL, india_path)

# UCI: tab-separated, no header, columns = label, message. quoting=3 keeps quote characters as text.
A_raw = pd.read_csv(uci_path, sep="\t", header=None, names=["label", "message"], quoting=3)
# India: CSV with columns Msg, Label (checked by reading the file, not assumed)
B_raw = pd.read_csv(india_path, encoding="utf-8")
print("Dataset B columns found:", B_raw.columns.tolist())
B_raw = B_raw.rename(columns={"Msg": "message", "Label": "label"})

print("\nDataset A, first 10 records")
display(A_raw.head(10)) if "display" in globals() else print(A_raw.head(10))
print("\nDataset B, first 10 records")
display(B_raw.head(10)) if "display" in globals() else print(B_raw.head(10))

# %% [markdown]
# ## 2. Audit both datasets
# Checks from the guide's audit checklist: size, classes, missing values, duplicates, message
# length, label conflicts, broken text, and provenance.

# %%
def audit(df, name):
    msg = df["message"].astype(str)
    return {
        "dataset": name,
        "total_rows": len(df),
        "ham": int((df["label"].astype(str).str.strip().str.lower() == "ham").sum()),
        "spam": int((df["label"].astype(str).str.strip().str.lower() == "spam").sum()),
        "missing_message": int(df["message"].isna().sum()),
        "missing_label": int(df["label"].isna().sum()),
        "exact_duplicate_messages": int(df["message"].duplicated().sum()),
        "duplicates_with_conflicting_labels": int(df.dropna().groupby("message")["label"].nunique().gt(1).sum()),
        "broken_encoding_rows": int(msg.str.contains(r"Ã|â€|Â").sum()),
        "rows_with_lost_characters_????": int(msg.str.contains(r"\?{4,}").sum()),
        "median_length_chars": float(msg.str.len().median()),
    }

audit_table = pd.DataFrame([audit(A_raw, "A: UCI SMS Spam Collection"), audit(B_raw, "B: India Spam SMS")])
audit_table.to_csv(f"{OUT}/tables/table0_raw_audit.csv", index=False)
audit_table.T

# %% [markdown]
# **Provenance (checked on the source pages)**
#
# | | Dataset A | Dataset B |
# |---|---|---|
# | Source | UCI Machine Learning Repository, Almeida, Gómez Hidalgo & Yamakami (2011) | GitHub `junioralive/india-spam-sms-classification` (also on Kaggle) |
# | Licence | CC BY 4.0 | MIT (2024) |
# | How it was collected | Documented in the 2011 paper (UK forum, NUS corpus, Caroline Tag's thesis, Grumbletext) | Crowd-sourced through a Google Form; no written labelling procedure |
# | Label meaning | spam = unsolicited commercial or fraudulent SMS | spam / ham, not defined further |
#
# Because Dataset B has no documented labelling procedure, the label spot-check below is required
# before using it as a target domain.

# %%
fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
for ax, (name, df) in zip(axes, [("A: UCI", A_raw), ("B: India", B_raw)]):
    df["label"].value_counts().reindex(["ham", "spam"]).plot.bar(ax=ax, color=["#4C72B0", "#C44E52"])
    ax.set_title(f"Class distribution, {name}"); ax.set_ylabel("messages"); ax.tick_params(axis="x", rotation=0)
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig1_class_distribution.png", dpi=200); plt.show()

fig, ax = plt.subplots(figsize=(7, 3.2))
for name, df, c in [("A: UCI", A_raw, "#4C72B0"), ("B: India", B_raw, "#DD8452")]:
    ax.hist(df["message"].astype(str).str.len().clip(upper=400), bins=40, alpha=0.6, label=name, color=c, density=True)
ax.set_xlabel("message length in characters (clipped at 400)"); ax.set_ylabel("share of messages"); ax.legend()
ax.set_title("Message length distribution")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig2_length_distribution.png", dpi=200); plt.show()

# %% [markdown]
# **Label spot-check.** Ten random messages of each class from Dataset B, to judge whether the labels
# are plausible (the guide asks for this before Dataset B is used).

# %%
for lab in ["spam", "ham"]:
    print(f"--- Dataset B, label = {lab} ---")
    for t in B_raw[B_raw["label"] == lab]["message"].dropna().sample(10, random_state=MAIN_SEED):
        print("  •", ftfy.fix_text(str(t))[:150])

# %% [markdown]
# ## 3. Cleaning and preprocessing (guide Prompt 3)
#
# The same steps are applied to both datasets, in this order. Each step's row count is recorded.
#
# 1. Map labels to spam = 1, ham = 0 and drop rows with a missing message or an invalid label.
# 2. Repair broken encoding with `ftfy` (Dataset B stores emoji and apostrophes as garbage such as
#    `Ã°Â\x9fÂ\x91Â\x8d`). Repairing is better than deleting, because the rest of the message is fine.
# 3. Lowercase, strip leading/trailing spaces, collapse repeated whitespace.
# 4. Remove exact duplicates inside each dataset (keep the first copy).
# 5. Remove from Dataset B any message that also appears in Dataset A.
#
# URLs, numbers and punctuation are **kept**: they are strong spam signals ("Click bit.ly/...", "Rs.5000").

# %%
LABEL_MAP = {"spam": 1, "ham": 0}

def clean_dataset(df, name, log):
    d = df.copy()
    log.append((name, "raw rows", len(d)))
    d["label"] = d["label"].astype(str).str.strip().str.lower().map(LABEL_MAP)
    d = d.dropna(subset=["message", "label"])
    d = d[d["message"].astype(str).str.strip() != ""]
    log.append((name, "after removing missing or invalid rows", len(d)))
    d["message"] = d["message"].astype(str).map(ftfy.fix_text)
    d["message"] = d["message"].str.lower().str.strip().str.replace(r"\s+", " ", regex=True)
    d = d[d["message"] != ""]
    d["label"] = d["label"].astype(int)
    before = len(d)
    d = d.drop_duplicates(subset="message", keep="first")
    log.append((name, f"after removing {before - len(d)} exact duplicates", len(d)))
    return d.reset_index(drop=True)

clean_log = []
A = clean_dataset(A_raw, "A", clean_log)
B = clean_dataset(B_raw, "B", clean_log)

cross = B["message"].isin(set(A["message"]))
print("Messages present in both datasets:", B.loc[cross, "message"].tolist())
B = B[~cross].reset_index(drop=True)
clean_log.append(("B", f"after removing {int(cross.sum())} message(s) also in A", len(B)))

conflicts = {n: int(df.groupby("message")["label"].nunique().gt(1).sum()) for n, df in [("A", A), ("B", B)]}
print("Messages with two different labels after cleaning:", conflicts)

steps = pd.DataFrame(clean_log, columns=["dataset", "step", "rows"])
steps.to_csv(f"{OUT}/tables/table1a_cleaning_steps.csv", index=False)
display(steps) if "display" in globals() else print(steps)

A["domain"], B["domain"] = "UCI", "India"
A.to_csv("data/clean/dataset_A_uci_clean.csv", index=False)
B.to_csv("data/clean/dataset_B_india_clean.csv", index=False)

# %%
def stats_row(raw, clean, name, provenance):
    return {"Dataset": name, "Total rows (raw)": len(raw), "Rows after cleaning": len(clean),
            "Ham": int((clean.label == 0).sum()), "Spam": int((clean.label == 1).sum()),
            "Spam share": f"{(clean.label == 1).mean():.1%}",
            "Missing removed": int(raw["message"].isna().sum()),
            "Duplicates removed": len(raw) - int(raw["message"].isna().sum()) - len(clean),
            "Notes / provenance": provenance}

table1 = pd.DataFrame([
    stats_row(A_raw, A, "UCI SMS Spam", "UCI repository, CC BY 4.0"),
    stats_row(B_raw, B, "Indian SMS candidate", "GitHub junioralive, MIT; crowd-sourced; 1 message shared with A removed"),
])
table1.to_csv(f"{OUT}/tables/table1_dataset_statistics.csv", index=False)
table1

# %% [markdown]
# ## 4. TF-IDF feature extraction (guide Prompt 4)
#
# TF-IDF turns each message into a vector of numbers. Each **row** is one message, each **column** is
# one word (or character piece), and the value is high when that piece is frequent in this message
# but rare across the training messages.
#
# * **Word TF-IDF:** unigrams and bigrams, at most 20,000 features (as the guide specifies).
# * **Character TF-IDF:** `char_wb`, 3- to 5-character pieces inside word boundaries. It can still
#   match "fr33" to "free" through shared pieces like "fr", and "offr" to "offer".
#
# **No leakage:** a vectorizer is always fitted on training data only and then used to transform test
# data. Here we only show the matrix sizes; the models are built in the next section.

# %%
FEATURES = {
    "word": dict(analyzer="word", ngram_range=(1, 2), max_features=20000),
    "char": dict(analyzer="char_wb", ngram_range=(3, 5)),
}
with open(f"{OUT}/feature_config.json", "w") as fh:
    json.dump({k: {**v, "ngram_range": list(v["ngram_range"])} for k, v in FEATURES.items()}, fh, indent=1)

A_tr, A_te = train_test_split(A, test_size=0.20, stratify=A["label"], random_state=MAIN_SEED)
for name, cfg in FEATURES.items():
    vec = TfidfVectorizer(**cfg).fit(A_tr["message"])          # fitted on Dataset A training data only
    X_tr, X_te, X_B = vec.transform(A_tr["message"]), vec.transform(A_te["message"]), vec.transform(B["message"])
    print(f"{name:5s} TF-IDF  A-train {X_tr.shape}  A-test {X_te.shape}  B {X_B.shape}  "
          f"(rows = messages, columns = features)")

# %% [markdown]
# ## 5. Baseline models on Dataset A (guide Prompt 5)
#
# * **Multinomial Naive Bayes:** counts how often each feature appears in spam and in ham and applies Bayes' rule.
# * **Logistic Regression:** learns one weight per feature; `class_weight="balanced"` because only 13% of
#   Dataset A is spam, so errors on spam would otherwise count too little.
# * **Linear SVM:** optional comparison, as the guide allows.
#
# Spam = 1 is the positive class. Split: 80% train / 20% test, stratified, random_state = 42.

# %%
BEST = {}   # hyperparameters chosen on Dataset A training data only (filled in below)

def make_model(model, params=None):
    params = params or {}
    if model == "naive_bayes":
        return MultinomialNB(**params)
    if model == "logistic_regression":
        return LogisticRegression(max_iter=1000, class_weight="balanced", **params)
    if model == "linear_svm":
        return LinearSVC(class_weight="balanced", **params)
    raise ValueError(model)

def make_pipeline(model, feature, params=None):
    if params is None:
        params = BEST.get((model, feature), {})
    return Pipeline([("tfidf", TfidfVectorizer(**FEATURES[feature])), ("clf", make_model(model, params))])

def scores(y, yhat):
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    return {"accuracy": accuracy_score(y, yhat), "precision": precision_score(y, yhat, zero_division=0),
            "recall": recall_score(y, yhat, zero_division=0), "f1": f1_score(y, yhat, zero_division=0),
            "macro_f1": f1_score(y, yhat, average="macro", zero_division=0),
            "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)}

MODELS = ["naive_bayes", "logistic_regression", "linear_svm"]
NICE = {"naive_bayes": "Naive Bayes", "logistic_regression": "Logistic Regression", "linear_svm": "Linear SVM"}

# %% [markdown]
# ### 5a. Choosing hyperparameters fairly
# Each model has one setting that matters: the smoothing `alpha` of Naive Bayes and the regularisation
# strength `C` of Logistic Regression and the SVM. We choose it by **5-fold cross-validation on Dataset A
# training data only** (spam F1). Dataset B is never looked at, as the guide requires. The chosen values
# are then fixed for every experiment and every seed.

# %%
from sklearn.model_selection import GridSearchCV, StratifiedKFold
GRID = {"naive_bayes": {"clf__alpha": [1.0, 0.3, 0.1, 0.03, 0.01]},
        "logistic_regression": {"clf__C": [0.1, 1, 10, 100]},
        "linear_svm": {"clf__C": [0.01, 0.1, 1, 10]}}
cv_rows = []
for model in MODELS:
    for feature in FEATURES:
        g = GridSearchCV(make_pipeline(model, feature, params={}), GRID[model], scoring="f1",
                         cv=StratifiedKFold(5, shuffle=True, random_state=MAIN_SEED)).fit(A_tr["message"], A_tr["label"])
        BEST[(model, feature)] = {k.replace("clf__", ""): v for k, v in g.best_params_.items()}
        cv_rows.append({"model": NICE[model], "feature": feature, "chosen": BEST[(model, feature)], "CV spam F1 on A-train": round(g.best_score_, 4)})
cv_table = pd.DataFrame(cv_rows)
cv_table.to_csv(f"{OUT}/tables/table_hyperparameters.csv", index=False)
cv_table

# %% [markdown]
# For comparison, Naive Bayes with the library default (`alpha = 1.0`). With TF-IDF features and only
# 12% spam in Dataset A, the default smoothing makes Naive Bayes predict "ham" for almost everything.

# %%
nb_default = make_pipeline("naive_bayes", "word", params={"alpha": 1.0}).fit(A_tr["message"], A_tr["label"])
nb_default_row = {"setting": "Naive Bayes, default alpha = 1.0, word TF-IDF",
                  "A-test F1": f1_score(A_te["label"], nb_default.predict(A_te["message"])),
                  "B F1": f1_score(B["label"], nb_default.predict(B["message"]))}
pd.DataFrame([nb_default_row]).to_csv(f"{OUT}/tables/table_nb_default_alpha.csv", index=False)
pd.DataFrame([nb_default_row]).round(4)

# %% [markdown]
# ### 5b. Baseline results with the chosen settings

# %%

source_models, rows = {}, []
for model in MODELS:
    pipe = make_pipeline(model, "word").fit(A_tr["message"], A_tr["label"])
    source_models[(model, "word")] = pipe
    s = scores(A_te["label"], pipe.predict(A_te["message"]))
    rows.append({"Model": NICE[model], "Feature": "Word TF-IDF", "Test domain": "Source A", **s})
    print(f"\n{NICE[model]} on Dataset A test (word TF-IDF)")
    print(classification_report(A_te["label"], pipe.predict(A_te["message"]), target_names=["ham", "spam"], digits=4))
baseline = pd.DataFrame(rows)
baseline.round(4)

# %%
fig, ax = plt.subplots(figsize=(6, 3))
ax.bar(baseline["Model"], baseline["f1"], color="#4C72B0")
for i, v in enumerate(baseline["f1"]):
    ax.text(i, v + 0.005, f"{v:.3f}", ha="center")
ax.set_ylim(0.8, 1.0); ax.set_ylabel("spam F1"); ax.set_title("Within-domain spam F1 on Dataset A (word TF-IDF)")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig3_baseline_f1.png", dpi=200); plt.show()

# %% [markdown]
# ## 6. Main experiment: cross-domain generalization (guide Prompt 6)
#
# The models trained above (Dataset A training data only, vectorizer fitted on A only) are applied
# **without any retraining** to all of Dataset B. The drop from source F1 to target F1 is the
# cross-domain gap.

# %%
rows = []
for feature in FEATURES:
    for model in MODELS:
        pipe = source_models.get((model, feature)) or make_pipeline(model, feature).fit(A_tr["message"], A_tr["label"])
        source_models[(model, feature)] = pipe
        sA = scores(A_te["label"], pipe.predict(A_te["message"]))
        sB = scores(B["label"], pipe.predict(B["message"]))
        rows.append({"Model": NICE[model], "Feature": feature, "Source A F1": sA["f1"], "Target B F1": sB["f1"],
                     "F1 gap (A - B)": sA["f1"] - sB["f1"], "Target accuracy": sB["accuracy"],
                     "Target precision": sB["precision"], "Target recall": sB["recall"],
                     "Target TN": sB["TN"], "Target FP": sB["FP"], "Target FN": sB["FN"], "Target TP": sB["TP"]})
cross_domain = pd.DataFrame(rows)
cross_domain.to_csv(f"{OUT}/tables/table2b_cross_domain_full_B.csv", index=False)
cross_domain.round(4)

# %%
# Table 2 in the guide's format (word TF-IDF, NB and LR, source test and all of Dataset B)
t2 = []
for model in ["naive_bayes", "logistic_regression"]:
    pipe = source_models[(model, "word")]
    for dom, X, y in [("Source A", A_te["message"], A_te["label"]), ("Target B", B["message"], B["label"])]:
        s = scores(y, pipe.predict(X))
        t2.append({"Model": NICE[model], "Feature": "Word TF-IDF", "Test domain": dom,
                   "Accuracy": s["accuracy"], "Precision": s["precision"], "Recall": s["recall"], "F1-score": s["f1"]})
table2 = pd.DataFrame(t2)
table2.to_csv(f"{OUT}/tables/table2_within_vs_cross_domain.csv", index=False)
table2.round(4)

# %% [markdown]
# ## 7. Why the domains differ: vocabulary and message characteristics
# Objective 3 of the guide. We measure how much of Dataset B's vocabulary was ever seen in Dataset A
# training data, and compare simple message characteristics.

# %%
tok = TfidfVectorizer(analyzer="word").build_analyzer()
vocab_A = set(w for t in A_tr["message"] for w in tok(t))

def oov_rate(text):
    words = tok(text)
    return np.mean([w not in vocab_A for w in words]) if words else np.nan

def characteristics(df, name):
    m = df["message"]
    return {"Domain": name, "Messages": len(df), "Median length (chars)": m.str.len().median(),
            "Has URL": m.str.contains(r"https?://|www\.|bit\.ly|\b\w+\.(?:com|in|ly|me)\b").mean(),
            "Has a number": m.str.contains(r"\d").mean(),
            "Has currency (rs/inr/₹/£)": m.str.contains(r"\brs\.?\b|\binr\b|₹|£").mean(),
            "Mean share of words unseen in A-train": m.map(oov_rate).mean()}

char_tab = pd.DataFrame([characteristics(A_te, "A test (UCI)"), characteristics(B, "B (India)"),
                         characteristics(B[B.label == 1], "B spam"), characteristics(B[B.label == 0], "B ham")])
char_tab.to_csv(f"{OUT}/tables/table7_domain_characteristics.csv", index=False)
vocab_B = set(w for t in B["message"] for w in tok(t))
print(f"Distinct words: A-train {len(vocab_A):,}, B {len(vocab_B):,}; "
      f"{len(vocab_B - vocab_A) / len(vocab_B):.1%} of B's distinct words never occur in A-train")
char_tab.round(3)

# %% [markdown]
# ## 8. Lightweight supervised domain adaptation (guide Prompt 7)
#
# For each seed:
# 1. Split Dataset A 80/20 and Dataset B 70/30 (adaptation pool / final target test), both stratified.
# 2. Take 0%, 10%, 20% and 40% of the adaptation pool (stratified sample).
# 3. Training data = Dataset A train + that sample. **Refit TF-IDF and the classifier on it.**
# 4. Evaluate on the same untouched final target test set.
#
# 0% is the source-only model. The final target test set is never used for training, fitting the
# vectorizer or choosing anything. A 100% row is added only as a reference for the upper end.

# %%
def run_seed(seed, fractions, models=("naive_bayes", "logistic_regression"), features=("word", "char")):
    a_tr, a_te = train_test_split(A, test_size=0.20, stratify=A["label"], random_state=seed)
    pool, b_te = train_test_split(B, test_size=0.30, stratify=B["label"], random_state=seed)
    out, preds = [], {}
    for frac in fractions:
        if frac == 0:
            add = pool.iloc[0:0]
        elif frac >= 1:
            add = pool
        else:
            add, _ = train_test_split(pool, train_size=frac, stratify=pool["label"], random_state=seed)
        train = pd.concat([a_tr, add])
        for model in models:
            for feature in features:
                pipe = make_pipeline(model, feature).fit(train["message"], train["label"])
                yb = pipe.predict(b_te["message"])
                sB = scores(b_te["label"], yb)
                sA = scores(a_te["label"], pipe.predict(a_te["message"]))
                preds[(model, feature, frac)] = yb
                out.append({"seed": seed, "model": model, "feature": feature, "target_fraction": frac,
                            "target_messages_added": len(add), "train_size": len(train),
                            **{f"B_{k}": v for k, v in sB.items()}, "A_f1": sA["f1"]})
    return pd.DataFrame(out), preds, b_te

all_runs, seed_preds, seed_tests = [], {}, {}
for seed in SEEDS:
    df_seed, preds, b_te = run_seed(seed, ADAPT_FRACTIONS + [REFERENCE_FRACTION])
    all_runs.append(df_seed); seed_preds[seed] = preds; seed_tests[seed] = b_te
    print(f"seed {seed}: pool {len(B) - len(b_te)} messages, final target test {len(b_te)} messages")
runs = pd.concat(all_runs, ignore_index=True)
runs.to_csv(f"{OUT}/tables/all_runs_per_seed.csv", index=False)

# %%
def mean_sd(df, keys, cols):
    g = df.groupby(keys)[cols].agg(["mean", "std"])
    g.columns = [f"{c}_{s}" for c, s in g.columns]
    return g.reset_index()

summary = mean_sd(runs, ["model", "feature", "target_fraction"], ["B_accuracy", "B_precision", "B_recall", "B_f1", "A_f1"])
summary.to_csv(f"{OUT}/tables/summary_mean_sd.csv", index=False)

def fmt(m, s):
    return f"{m:.4f} ± {s:.4f}"

t3 = []
for model in ["naive_bayes", "logistic_regression"]:
    for frac in ADAPT_FRACTIONS + [REFERENCE_FRACTION]:
        r = summary[(summary.model == model) & (summary.feature == "word") & (summary.target_fraction == frac)].iloc[0]
        label = "0% (source-only)" if frac == 0 else ("100% (reference)" if frac >= 1 else f"{int(frac * 100)}%")
        t3.append({"Model": NICE[model], "Target adaptation data": label,
                   "Accuracy": fmt(r.B_accuracy_mean, r.B_accuracy_std), "Precision": fmt(r.B_precision_mean, r.B_precision_std),
                   "Recall": fmt(r.B_recall_mean, r.B_recall_std), "F1-score": fmt(r.B_f1_mean, r.B_f1_std),
                   "Source A F1": fmt(r.A_f1_mean, r.A_f1_std)})
table3 = pd.DataFrame(t3)
table3.to_csv(f"{OUT}/tables/table3_domain_adaptation_word.csv", index=False)
print("Table 3 (word TF-IDF), mean ± SD over seeds", SEEDS)
table3

# %%
fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
for ax, feature in zip(axes, ["word", "char"]):
    for model, c in [("naive_bayes", "#DD8452"), ("logistic_regression", "#4C72B0")]:
        r = summary[(summary.model == model) & (summary.feature == feature) & (summary.target_fraction < 1)]
        ax.errorbar(r.target_fraction * 100, r.B_f1_mean, yerr=r.B_f1_std, marker="o", capsize=4, color=c, label=NICE[model])
    ax.set_title(f"{feature} TF-IDF"); ax.set_xlabel("% of target adaptation pool added"); ax.set_xticks([0, 10, 20, 40])
axes[0].set_ylabel("spam F1 on final target test (mean ± SD)"); axes[0].legend()
plt.suptitle("Effect of adding labelled Indian messages to training")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig4_adaptation_curve.png", dpi=200); plt.show()

# %% [markdown]
# ## 8b. Robustness check: are near-copies inflating the adaptation gain?
#
# Indian promotional SMS are sent from templates ("Get 5GB free data... click ..."). With a random 70/30
# split, a near-copy of a test message can sit in the adaptation pool, and the model then "recognises"
# the template instead of generalising. We group near-duplicates with **MinHash** (estimated Jaccard
# similarity ≥ 0.6 on word 3-shingles, after replacing links and digits) and repeat the adaptation
# experiment with a **group-aware split**: every near-duplicate group goes wholly to the pool or wholly
# to the test set.

# %%
try:
    from datasketch import MinHash, MinHashLSH
except ImportError:
    os.system("pip -q install datasketch")
    from datasketch import MinHash, MinHashLSH
from sklearn.model_selection import GroupShuffleSplit

def shingle_words(t):
    t = re.sub(r"https?://\S+|\S+\.(com|in|ly|me)\S*", " url ", t)
    t = re.sub(r"\d+", "0", t)
    return re.sub(r"[^a-z0 ]+", " ", t).split()

lsh, groups, first = MinHashLSH(threshold=0.6, num_perm=96), [], {}
for i, t in enumerate(B["message"]):
    w = shingle_words(t)
    h = MinHash(num_perm=96)
    for sh in {" ".join(w[j:j + 3]) for j in range(max(1, len(w) - 2))}:
        h.update(sh.encode())
    hit, key = lsh.query(h), f"g{i}"
    if hit:
        groups.append(first[min(hit)])
    else:
        lsh.insert(key, h); first[key] = key; groups.append(key)
B["group"] = groups
print(f"Dataset B: {len(B)} messages form {B['group'].nunique()} near-duplicate groups "
      f"(largest {B['group'].value_counts().iloc[0]} messages)")

leak_rows = []
for seed in SEEDS:
    pool_r, test_r = train_test_split(B, test_size=0.30, stratify=B["label"], random_state=seed)
    leak = test_r["group"].isin(set(pool_r["group"]))
    leak_rows.append({"seed": seed, "test messages": len(test_r), "with a near-copy in the pool": int(leak.sum()),
                      "spam test messages with a near-copy": int((leak & (test_r.label == 1)).sum()),
                      "spam test messages": int((test_r.label == 1).sum())})
leak_table = pd.DataFrame(leak_rows)
leak_table.to_csv(f"{OUT}/tables/table9a_random_split_leakage.csv", index=False)
display(leak_table) if "display" in globals() else print(leak_table)

grouped = []
for seed in SEEDS:
    pi, ti = next(GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=seed).split(B, B["label"], B["group"]))
    pool_g, test_g = B.iloc[pi], B.iloc[ti]
    a_tr_s, _ = train_test_split(A, test_size=0.20, stratify=A["label"], random_state=seed)
    for frac in ADAPT_FRACTIONS:
        add = pool_g.iloc[0:0] if frac == 0 else train_test_split(pool_g, train_size=frac, stratify=pool_g["label"], random_state=seed)[0]
        train = pd.concat([a_tr_s, add])
        for model in ["naive_bayes", "logistic_regression"]:
            pipe = make_pipeline(model, "word").fit(train["message"], train["label"])
            s_ = scores(test_g["label"], pipe.predict(test_g["message"]))
            grouped.append({"seed": seed, "model": model, "target_fraction": frac, "B_f1": s_["f1"]})
grouped = pd.DataFrame(grouped)
g_sum = grouped.groupby(["model", "target_fraction"]).B_f1.agg(["mean", "std"]).reset_index()
r_sum = summary[summary.feature == "word"][["model", "target_fraction", "B_f1_mean", "B_f1_std"]]
t9 = g_sum.merge(r_sum, on=["model", "target_fraction"])
t9 = pd.DataFrame({"Model": t9.model.map(NICE), "Target data added": (t9.target_fraction * 100).astype(int).astype(str) + "%",
                   "F1, random split": [fmt(m, s) for m, s in zip(t9.B_f1_mean, t9.B_f1_std)],
                   "F1, group-aware split": [fmt(m, s) for m, s in zip(t9["mean"], t9["std"])]})
t9.to_csv(f"{OUT}/tables/table9_group_aware_split.csv", index=False)
t9

# %% [markdown]
# ## 9. Word versus character TF-IDF (guide Prompt 8)
# Same splits, same models; only the feature representation changes. Source-only models (0%).

# %%
t4 = []
for model in ["naive_bayes", "logistic_regression"]:
    for feature, fname in [("word", "Word TF-IDF"), ("char", "Character TF-IDF")]:
        r = summary[(summary.model == model) & (summary.feature == feature) & (summary.target_fraction == 0)].iloc[0]
        t4.append({"Model": NICE[model], "Feature representation": fname, "Source F1": fmt(r.A_f1_mean, r.A_f1_std),
                   "Target F1": fmt(r.B_f1_mean, r.B_f1_std), "Target precision": fmt(r.B_precision_mean, r.B_precision_std),
                   "Target recall": fmt(r.B_recall_mean, r.B_recall_std)})
table4 = pd.DataFrame(t4)
table4.to_csv(f"{OUT}/tables/table4_word_vs_char.csv", index=False)
table4

# %%
fig, ax = plt.subplots(figsize=(7, 3.2))
labels, vals, errs, cols = [], [], [], []
for model in ["naive_bayes", "logistic_regression"]:
    for feature, c in [("word", "#4C72B0"), ("char", "#55A868")]:
        r = summary[(summary.model == model) & (summary.feature == feature) & (summary.target_fraction == 0)].iloc[0]
        labels.append(f"{NICE[model]}\n{feature}"); vals.append(r.B_f1_mean); errs.append(r.B_f1_std); cols.append(c)
ax.bar(labels, vals, yerr=errs, capsize=4, color=cols)
ax.set_ylabel("target spam F1 (source-only)"); ax.set_title("Word vs character TF-IDF on Dataset B")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig5_word_vs_char.png", dpi=200); plt.show()

# %% [markdown]
# ## 10. Error analysis (guide Prompt 9)
#
# Logistic Regression with word TF-IDF, seed 42: errors of the source-only model and of the model adapted
# with 40% of the pool, on the same final target test set.
#
# The `suggested_category` column is filled by simple, visible rules (listed below) **only as a starting
# point**. The guide asks students to verify every category by hand in the `manual_category` column;
# the counts below are of the rule suggestions, not of verified categories.

# %%
b_te42 = seed_tests[MAIN_SEED].copy()
src_pred = seed_preds[MAIN_SEED][("logistic_regression", "word", 0.0)]
ada_pred = seed_preds[MAIN_SEED][("logistic_regression", "word", 0.40)]

PROMO = re.compile(r"\b(offer|cashback|discount|sale|off|deal|shop|free|bonus|reward|coupon|recharge|data|plan|order now|hurry)\b")
URLNUM = re.compile(r"https?://|www\.|bit\.ly|\b\w+\.(com|in|ly)\b|\d{4,}")

def suggest(text, label):
    words = tok(text)
    oov = np.mean([w not in vocab_A for w in words]) if words else 0
    if re.search(r"\?{4,}", text):
        return "lost characters (????)"
    if len(words) <= 3:
        return "very short / ambiguous"
    if oov >= 0.5:
        return "unfamiliar vocabulary"
    if label == 1 and PROMO.search(text):
        return "promotional language"
    if URLNUM.search(text):
        return "URL / number variation"
    if label == 0:
        return "ambiguous legitimate message"
    return "other"

def error_frame(pred, setting):
    e = b_te42.assign(predicted=pred)
    e = e[e["predicted"] != e["label"]].copy()
    e["error_type"] = np.where(e["label"] == 0, "false positive (ham → spam)", "false negative (spam → ham)")
    e["share_words_unseen_in_A"] = e["message"].map(oov_rate).round(3)
    e["suggested_category"] = [suggest(t, l) for t, l in zip(e["message"], e["label"])]
    e["manual_category"] = ""   # to be filled in by the students after reading each message
    e["setting"] = setting
    return e[["setting", "error_type", "message", "label", "predicted", "share_words_unseen_in_A",
              "suggested_category", "manual_category"]]

errors = pd.concat([error_frame(src_pred, "source-only"), error_frame(ada_pred, "adapted 40%")], ignore_index=True)
errors.to_csv(f"{OUT}/tables/error_annotation_template.csv", index=False)
print(errors.groupby(["setting", "error_type"]).size().rename("errors"))
errors.head(50)

# %%
counts = errors.groupby(["suggested_category", "setting"]).size().unstack(fill_value=0)
counts = counts.reindex(columns=["source-only", "adapted 40%"], fill_value=0)
counts.to_csv(f"{OUT}/tables/table5_error_categories_suggested.csv")
ax = counts.plot.barh(figsize=(7, 3.6), color=["#C44E52", "#4C72B0"])
ax.set_xlabel("errors on the final target test (seed 42, LR word)"); ax.set_ylabel("")
ax.set_title("Error categories, rule-suggested (to be verified by hand)")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig6_error_categories.png", dpi=200); plt.show()
counts

# %% [markdown]
# ## 11. Statistical analysis (guide Prompt 10)
#
# * **Mean ± SD** over three seeds is in Tables 3 and 4.
# * **Consistency:** does adaptation raise F1 in every seed, not only on average?
# * **McNemar's test** compares two models on the *same* test messages using only the messages where
#   they disagree (b = only model 1 right, c = only model 2 right). It is the right paired test here
#   because both models are scored on identical messages. With three seeds we report the test per seed
#   rather than claiming a general significance.

# %%
delta_rows = []
for seed in SEEDS:
    for model in ["naive_bayes", "logistic_regression"]:
        for feature in ["word", "char"]:
            base = runs[(runs.seed == seed) & (runs.model == model) & (runs.feature == feature) & (runs.target_fraction == 0)].B_f1.iloc[0]
            for frac in [0.10, 0.20, 0.40]:
                f = runs[(runs.seed == seed) & (runs.model == model) & (runs.feature == feature) & (runs.target_fraction == frac)].B_f1.iloc[0]
                y = seed_tests[seed]["label"].values
                p0, p1 = seed_preds[seed][(model, feature, 0.0)], seed_preds[seed][(model, feature, frac)]
                b = int(((p0 == y) & (p1 != y)).sum()); c = int(((p0 != y) & (p1 == y)).sum())
                pval = binomtest(min(b, c), b + c, 0.5).pvalue if b + c else 1.0
                delta_rows.append({"seed": seed, "model": NICE[model], "feature": feature, "fraction": f"{int(frac * 100)}%",
                                   "F1 source-only": base, "F1 adapted": f, "ΔF1": f - base,
                                   "only source-only right (b)": b, "only adapted right (c)": c, "McNemar p": pval})
deltas = pd.DataFrame(delta_rows)
deltas.to_csv(f"{OUT}/tables/table6b_delta_f1_mcnemar.csv", index=False)

consistency = deltas.groupby(["model", "feature", "fraction"]).agg(
    mean_delta_F1=("ΔF1", "mean"), sd_delta_F1=("ΔF1", "std"),
    seeds_improved=("ΔF1", lambda s: f"{int((s > 0).sum())}/{len(s)}"),
    seeds_p_below_0_05=("McNemar p", lambda s: f"{int((s < 0.05).sum())}/{len(s)}")).reset_index()
consistency.to_csv(f"{OUT}/tables/table8_consistency.csv", index=False)
consistency.round(4)

# %%
# Table 6: confusion matrices on the final target test set (seed 42, word TF-IDF)
t6 = []
for model in ["naive_bayes", "logistic_regression"]:
    for frac, name in [(0.0, "Source-only on target B"), (0.40, "Adapted (40%) on target B")]:
        r = runs[(runs.seed == MAIN_SEED) & (runs.model == model) & (runs.feature == "word") & (runs.target_fraction == frac)].iloc[0]
        t6.append({"Evaluation setting": f"{name}, {NICE[model]}", "TN": r.B_TN, "FP": r.B_FP, "FN": r.B_FN, "TP": r.B_TP})
table6 = pd.DataFrame(t6)
table6.to_csv(f"{OUT}/tables/table6_confusion_matrices.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(8, 3.4))
for ax, (frac, title) in zip(axes, [(0.0, "Source-only"), (0.40, "Adapted 40%")]):
    r = runs[(runs.seed == MAIN_SEED) & (runs.model == "logistic_regression") & (runs.feature == "word") & (runs.target_fraction == frac)].iloc[0]
    cm = np.array([[r.B_TN, r.B_FP], [r.B_FN, r.B_TP]])
    ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=13, color="black")
    ax.set_xticks([0, 1], ["pred ham", "pred spam"]); ax.set_yticks([0, 1], ["true ham", "true spam"])
    ax.set_title(f"LR word, {title} (seed 42)")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/fig7_confusion_matrices.png", dpi=200); plt.show()
table6

# %% [markdown]
# ## 12. Save the models used by the application
# Two Logistic Regression models with word TF-IDF (seed 42) are saved with joblib, together with Naive
# Bayes versions: the **baseline** (Dataset A only) and the **adapted** model (Dataset A + 40% of the
# target pool). The app loads these files and never retrains.

# %%
a_tr, _ = train_test_split(A, test_size=0.20, stratify=A["label"], random_state=MAIN_SEED)
pool, b_te = train_test_split(B, test_size=0.30, stratify=B["label"], random_state=MAIN_SEED)
add40, _ = train_test_split(pool, train_size=0.40, stratify=pool["label"], random_state=MAIN_SEED)
saved = {}
for model in ["logistic_regression", "naive_bayes"]:
    for tag, train in [("baseline", a_tr), ("adapted40", pd.concat([a_tr, add40]))]:
        pipe = make_pipeline(model, "word").fit(train["message"], train["label"])
        path = f"{OUT}/models/{model}_word_{tag}.joblib"
        joblib.dump(pipe, path)
        saved[f"{model}_word_{tag}"] = {"path": path, "train_messages": len(train), "seed": MAIN_SEED,
                                         "target_test_f1": scores(b_te["label"], pipe.predict(b_te["message"]))["f1"]}

results = {
    "seeds": SEEDS, "hyperparameters": {f"{m}|{f}": v for (m, f), v in BEST.items()}, "group_aware": t9.to_dict("records"), "nb_default_alpha": nb_default_row, "adapt_fractions": ADAPT_FRACTIONS, "features": FEATURES,
    "dataset_statistics": table1.to_dict("records"), "cleaning_steps": steps.to_dict("records"),
    "within_vs_cross": table2.to_dict("records"), "cross_domain_full_B": cross_domain.to_dict("records"),
    "domain_characteristics": char_tab.to_dict("records"),
    "adaptation_summary": summary.to_dict("records"), "consistency": consistency.to_dict("records"),
    "confusion_seed42": table6.to_dict("records"), "saved_models": saved,
    "versions": {"pandas": pd.__version__, "numpy": np.__version__, "scikit-learn": sklearn.__version__},
}
with open(f"{OUT}/results.json", "w") as fh:
    json.dump(results, fh, indent=1, default=str)
print(json.dumps(saved, indent=1))
