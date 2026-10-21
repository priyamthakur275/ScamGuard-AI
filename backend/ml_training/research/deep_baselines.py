"""Deep-learning baselines on ScamGuard-IN-2026 (same campaign-aware split as run_experiments.py).

    python -m ml_training.research.deep_baselines

Trains two TensorFlow/Keras text classifiers on the training split, early-stops on the
development split, and scores the real test split (1,874 messages from unseen campaigns):

* char_cnn  - character embeddings + parallel 1-D convolutions (kernel 3/5/7) + global max pooling
* word_bilstm - word embeddings + bidirectional LSTM + global max pooling

Writes ml_training/research/deep_results.json. Uses the same text cleaning (prep) and the
same Scores / McNemar helpers as the main experiments, so the numbers are comparable.
"""

from __future__ import annotations

import json
import os
import random
import time

import numpy as np
import pandas as pd

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf  # noqa: E402
from tensorflow.keras import layers  # noqa: E402

from ml_training.research.run_experiments import DS, Scores, fit_predict, mcnemar, prep  # noqa: E402

HERE = os.path.dirname(__file__)
SEED = 2026


def seed_all():
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)


def char_cnn(vec):
    inp = layers.Input(shape=(vec.get_config()["output_sequence_length"],), dtype="int64")
    x = layers.Embedding(vec.vocabulary_size(), 48)(inp)
    branches = []
    for k in (3, 5, 7):
        b = layers.Conv1D(96, k, activation="relu", padding="same")(x)
        branches.append(layers.GlobalMaxPooling1D()(b))
    x = layers.Concatenate()(branches)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(64, activation="relu")(x)
    out = layers.Dense(1, activation="sigmoid")(x)
    return tf.keras.Model(inp, out)


def word_bilstm(vec):
    inp = layers.Input(shape=(vec.get_config()["output_sequence_length"],), dtype="int64")
    x = layers.Embedding(vec.vocabulary_size(), 96, mask_zero=True)(inp)
    x = layers.Bidirectional(layers.LSTM(64, return_sequences=True))(x)
    x = layers.GlobalMaxPooling1D()(x)
    x = layers.Dropout(0.4)(x)
    out = layers.Dense(1, activation="sigmoid")(x)
    return tf.keras.Model(inp, out)


def train_one(name, build, vec, tr, dev, tests):
    seed_all()
    ytr = (tr.label == "scam").astype(int).values
    ydv = (dev.label == "scam").astype(int).values
    vec.adapt(tf.constant(prep(tr.text)))
    enc = lambda texts: vec(tf.constant(prep(texts))).numpy()
    xtr, xdv = enc(tr.text), enc(dev.text)
    model = build(vec)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="binary_crossentropy",
                  metrics=[tf.keras.metrics.AUC(name="auc")])
    pos = ytr.mean()
    cw = {0: 0.5 / (1 - pos), 1: 0.5 / pos}
    t0 = time.time()
    hist = model.fit(xtr, ytr, validation_data=(xdv, ydv), epochs=15, batch_size=64,
                     class_weight=cw, verbose=2,
                     callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=3, restore_best_weights=True)])
    secs = time.time() - t0
    res = {"epochs_run": len(hist.history["loss"]), "train_seconds": round(secs, 1), "params": int(model.count_params())}
    probs = {}
    for k, d in tests.items():
        p = model.predict(enc(d.text), verbose=0).ravel()
        probs[k] = p
        res[k] = Scores((d.label == "scam").astype(int).values, p).metrics(boot=1000)
    return res, probs


def main() -> int:
    df = pd.read_csv(DS)
    tr, dev, test = df[df.split == "train"], df[df.split == "dev"], df[df.split == "test"]
    tests = {"real_test": test}
    R = {"protocol": "train on train split, early stopping on dev split, evaluate on real test split (campaign-held-out)",
         "train_rows": int(len(tr)), "dev_rows": int(len(dev)), "test_rows": int(len(test))}

    cvec = layers.TextVectorization(split="character", output_mode="int", output_sequence_length=320, max_tokens=400)
    wvec = layers.TextVectorization(output_mode="int", output_sequence_length=80, max_tokens=20000)
    probs = {}
    for name, build, vec in (("char_cnn", char_cnn, cvec), ("word_bilstm", word_bilstm, wvec)):
        R[name], probs[name] = train_one(name, build, vec, tr, dev, tests)
        m = R[name]["real_test"]
        print(name, "F1", round(m["f1"], 4), "FAR", round(m["fpr"], 4), "AUC", round(m["roc_auc"], 4))

    # same-protocol logistic-regression reference (train split only) for a paired comparison
    s, _ = fit_predict(tr, tests)
    y = s["real_test"].y
    R["logistic_regression_same_protocol"] = s["real_test"].metrics(boot=1000)
    for name in ("char_cnn", "word_bilstm"):
        R[f"mcnemar_lr_vs_{name}"] = mcnemar(y, s["real_test"].p, probs[name]["real_test"])
    with open(os.path.join(HERE, "deep_results.json"), "w") as fh:
        json.dump(R, fh, indent=1)
    print(json.dumps({k: (round(v["f1"], 4), round(v["fpr"], 4)) for k, v in
                      {"lr": R["logistic_regression_same_protocol"], "cnn": R["char_cnn"]["real_test"], "bilstm": R["word_bilstm"]["real_test"]}.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
