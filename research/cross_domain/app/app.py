"""Cross-Domain SMS Spam Detection System (Streamlit).

Run from the project folder:
    pip install -r app/requirements.txt
    streamlit run app/app.py

The app only loads models saved by the notebook (outputs/models/*.joblib). It never retrains,
and it never reads the final target test set.
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")

MODELS = {
    ("Logistic Regression", "Baseline (trained on UCI only)"): "logistic_regression_word_baseline",
    ("Logistic Regression", "Adapted (UCI + 40% of Indian pool)"): "logistic_regression_word_adapted40",
    ("Naive Bayes", "Baseline (trained on UCI only)"): "naive_bayes_word_baseline",
    ("Naive Bayes", "Adapted (UCI + 40% of Indian pool)"): "naive_bayes_word_adapted40",
}

st.set_page_config(page_title="Cross-Domain SMS Spam Detection System", layout="wide")


@st.cache_resource
def load_model(key):
    return joblib.load(os.path.join(OUT, "models", f"{key}.joblib"))


@st.cache_data
def load_results():
    with open(os.path.join(OUT, "results.json")) as fh:
        return json.load(fh)


def explain(pipe, text, k=8):
    """Top features behind this prediction.

    Logistic Regression: contribution = TF-IDF value x learned weight.
    Naive Bayes: contribution = TF-IDF value x (log P(feature|spam) - log P(feature|ham)).
    Positive values push towards spam, negative towards ham.
    """
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    x = vec.transform([text]).tocsr()
    names = vec.get_feature_names_out()
    if hasattr(clf, "coef_") and not hasattr(clf, "feature_log_prob_"):
        w = clf.coef_[0]
    else:
        w = clf.feature_log_prob_[1] - clf.feature_log_prob_[0]
    contrib = [(names[j], float(x[0, j] * w[j])) for j in x.indices]
    contrib.sort(key=lambda t: -abs(t[1]))
    return pd.DataFrame(contrib[:k], columns=["feature", "contribution"])


st.title("Cross-Domain SMS Spam Detection System")
st.caption("Models trained on the UCI SMS Spam Collection (UK) and adapted with labelled Indian SMS. "
           "Spam = unwanted promotional or fraudulent SMS; ham = normal message.")

tab_check, tab_results = st.tabs(["Check a message", "Experiment dashboard"])

with tab_check:
    c1, c2 = st.columns(2)
    model_name = c1.selectbox("Classifier", ["Logistic Regression", "Naive Bayes"])
    variant = c2.radio("Model version", ["Baseline (trained on UCI only)", "Adapted (UCI + 40% of Indian pool)"])
    key = MODELS[(model_name, variant)]
    pipe = load_model(key)
    info = load_results()["saved_models"][key]
    st.caption(f"Model file: `outputs/models/{key}.joblib` · word TF-IDF · trained on "
               f"{info['train_messages']:,} messages · seed {info['seed']} · "
               f"spam F1 on the Indian final test set: {info['target_test_f1']:.3f}")

    text = st.text_area("Enter an SMS message", height=110,
                        placeholder="e.g. CONGRATULATIONS! FREE 2GB data is yours! Claim on the app now. Hurry i.airtel.in/e/...")
    if st.button("Classify", type="primary") and text.strip():
        clean = " ".join(text.lower().split())  # the same basic cleaning as in the notebook
        p_spam = float(pipe.predict_proba([clean])[0, 1])
        label = "SPAM" if p_spam >= 0.5 else "HAM"
        (st.error if label == "SPAM" else st.success)(f"**{label}**, probability of spam = {p_spam:.3f}")
        st.write("**Features that influenced this prediction** (positive = towards spam, negative = towards ham)")
        st.bar_chart(explain(pipe, clean).set_index("feature"))

with tab_results:
    R = load_results()
    st.subheader("Within-domain vs cross-domain (trained on UCI only)")
    st.dataframe(pd.DataFrame(R["within_vs_cross"]).round(4), hide_index=True)
    st.subheader("Domain adaptation: spam F1 on the Indian final test set (mean over 3 seeds)")
    s = pd.DataFrame(R["adaptation_summary"])
    s = s[(s.target_fraction < 1)]
    curve = s.pivot_table(index="target_fraction", columns=["model", "feature"], values="B_f1_mean")
    curve.index = [f"{int(f * 100)}%" for f in curve.index]
    curve.columns = [f"{m.replace('_', ' ')} ({f})" for m, f in curve.columns]
    st.line_chart(curve)
    st.subheader("Confusion matrices (seed 42, word TF-IDF, Indian final test set)")
    st.dataframe(pd.DataFrame(R["confusion_seed42"]), hide_index=True)
    fig = os.path.join(OUT, "figures", "fig7_confusion_matrices.png")
    if os.path.exists(fig):
        st.image(fig)
