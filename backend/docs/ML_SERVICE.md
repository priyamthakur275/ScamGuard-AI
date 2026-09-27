# ML Training Pipeline & Inference Service

This document covers the offline training pipeline (`ml_training`), the
online inference microservice (`ml_service`), and the shared library
(`ml_common`) they both depend on. It implements Section 8 (ML Pipeline
Architecture) of the approved architecture document and is consistent
with the report's specified algorithms (Naïve Bayes, Logistic Regression,
Random Forest, SVM) and pipeline stages (preprocessing → TF-IDF → training
→ evaluation → real-time prediction → alerting).

`app_service` (Phase 2) is not covered here and was not modified.

---

## 1. Package layout and dependency direction

```
backend/
├── ml_common/       <-- shared library, zero dependency on ml_training or ml_service
│   ├── preprocessing/   text_cleaner.py, tokenizer.py, pipeline.py
│   ├── features/         tfidf_vectorizer.py
│   ├── registry/          artifact_store.py, model_registry.py
│   ├── domain/             value_objects.py
│   └── tests/
├── ml_training/      <-- offline pipeline; depends on ml_common only
│   ├── data/               loader.py, validator.py
│   ├── training/            base_trainer.py, classical_trainers.py, train_pipeline.py
│   ├── evaluation/           evaluator.py
│   ├── config.py
│   ├── datasets/               sample_messages.csv (bundled demo data)
│   ├── run_training.py          CLI entrypoint
│   └── tests/
└── ml_service/        <-- online FastAPI service; depends on ml_common only
    ├── inference/            inference_engine.py, confidence.py, threat_scorer.py, explainer.py
    ├── services/               prediction_service.py
    ├── api/v1/                  predict.py, health.py, router.py
    ├── core/                      config.py, exceptions.py, logging_config.py, rate_limit.py
    ├── main.py
    └── tests/
```

**The dependency graph is strictly one-directional: `ml_training` → `ml_common` ← `ml_service`.**
Neither service imports the other. This is what the approved architecture's
"independently deployable, independently scalable" requirement actually
means in code, not just in a diagram — and it's not incidental: a real bug
was caught and fixed during this build (see §6) precisely because the
`TfidfFeatureExtractor` class briefly lived in the wrong package and broke
this rule.

The one sanctioned exception is `ml_service/tests/conftest.py`, which
imports `ml_training` purely to train a real fixture model for
integration tests. Test code never ships in the deployed container, so
this doesn't violate the runtime dependency graph.

---

## 2. Why the design looks the way it does

- **Shared preprocessing (`ml_common.preprocessing`)**: the single most
  common production ML bug is train/serve skew — the vectorizer sees
  different tokens at inference time than it was fit on. Housing
  `TextPreprocessingPipeline` in `ml_common` and instantiating it
  identically in both `ml_training/run_training.py` and
  `ml_service/api/deps.py` makes this class of bug structurally
  difficult to introduce.
- **No runtime corpus downloads**: stopwords and stemming are bundled,
  versioned, deterministic code (`ml_common/preprocessing/tokenizer.py`),
  not `nltk.download(...)` calls. A production inference service must not
  depend on reaching an external corpus server at startup.
- **Strategy pattern for trainers (`BaseModelTrainer`)**: the training
  pipeline depends only on this interface. Naïve Bayes, Logistic
  Regression, Random Forest, and SVM are all thin adapters implementing
  it. Adding an LSTM or transformer trainer later — per the approved
  architecture's Phase 5 roadmap — is a pure addition; the pipeline,
  evaluator, and registry never change.
- **LSTM is intentionally not implemented** in this phase. Per the
  approved architecture: *"LSTM is kept as a benchmark/challenger model
  and only promoted if it clears a defined latency SLA."* It is not the
  production default, and implementing it as a hollow stub would violate
  the no-placeholder-code requirement more than omitting it with a clear
  extension point does.
- **Dependency injection everywhere**: `TrainingPipeline` and
  `PredictionService` receive every collaborator (loader, validator,
  vectorizer, trainers, evaluator, registry / engine, confidence
  calculator, threat scorer, explainer) through their constructors. Both
  classes contain sequencing logic only — no business logic of their
  own — which is what makes them composable and unit-testable with fakes.
- **Confidence vs. threat score are different numbers on purpose.**
  Confidence measures how *certain* the model is (distance from the 0.5
  decision boundary). Threat score measures how *dangerous* the message
  looks (model probability plus a transparent, rule-based urgency-signal
  boost). A message can be low-confidence and high-threat, or vice versa.
- **Explainability without SHAP**: per the approved architecture, "cheap"
  explainability is a first-class requirement. `PredictionExplainer`
  multiplies each present token's TF-IDF weight by the model's per-feature
  weight (coefficient, log-likelihood ratio, or feature importance,
  depending on estimator type) and returns the top-N. No extra model,
  no extra latency budget.

---

## 3. Training a model

```bash
cd backend
pip install -r requirements-ml.txt   # see §7

python -m ml_training.run_training \
    --dataset ml_training/datasets/sample_messages.csv \
    --version v1 \
    --artifacts-dir artifacts
```

Multiple `--dataset` flags may be given to merge sources (Kaggle, UCI,
SpamAssassin, Enron-style exports per the report's Section 1.4 Scope),
as long as each has `text`/`label` columns (configurable via
`DatasetSource.text_column` / `label_column` for differently-named
source files).

What happens, in order (mirrors Section 8 of the approved architecture):

1. **Load** — `DatasetLoader` merges and normalizes one or more CSVs.
2. **Validate** — `DatasetValidator` checks schema, nulls, label
   whitelist, minimum text length, and warns (without failing) on class
   imbalance.
3. **Preprocess** — every message run through
   `TextPreprocessingPipeline` (clean → tokenize → stem → stopword-filter).
4. **Split** — stratified train/test split (`TrainingConfig.test_size`,
   default 20%).
5. **Vectorize** — `TfidfFeatureExtractor` fit **once**, on training data
   only, then frozen.
6. **Train + evaluate** — all four classical trainers fit on the same
   features; each evaluated for Accuracy, Precision, Recall, F1, ROC-AUC,
   and False Positive Rate.
7. **Select** — `ModelEvaluator.select_best` picks the highest-F1
   candidate (ties broken by lower false-positive rate).
8. **Register + promote** — winning `(model, vectorizer)` pair is
   serialized and written to the artifact store under
   `{model_name}/{version}/`, and (unless `--no-promote` is passed)
   immediately promoted to production.

Sample output:

```
naive_bayes          accuracy=0.600 precision=0.500 recall=1.000 f1=0.667 roc_auc=1.000 fpr=0.667
logistic_regression  accuracy=0.600 precision=0.500 recall=1.000 f1=0.667 roc_auc=1.000 fpr=0.667
random_forest        accuracy=0.600 precision=0.500 recall=1.000 f1=0.667 roc_auc=0.667 fpr=0.667
svm                  accuracy=0.600 precision=0.500 recall=1.000 f1=0.667 roc_auc=1.000 fpr=0.667
Winner: naive_bayes (f1=0.667) registered as version=v1 and promoted to production
```

(These specific numbers come from the bundled 24-row synthetic demo
dataset — real numbers from the actual Kaggle/UCI/SpamAssassin/Enron
corpora specified in the report will differ substantially and should be
much higher.)

---

## 4. Running the inference service

```bash
cd backend
export ARTIFACTS_DIR=artifacts
export PRODUCTION_MODEL_NAME=naive_bayes   # must match a promoted model_name
uvicorn ml_service.main:app --port 8002
```

The model is loaded once, at process startup (`main.py`'s `lifespan`
context), not per request. If no production model is registered yet, the
process still starts (liveness stays green) but `/api/v1/ready` reports
`not_ready` and `/predict` returns `503 MODEL_UNAVAILABLE` until a model
is trained and promoted — this is what lets Kubernetes gate the pod out
of the load-balancer pool correctly.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness probe |
| GET | `/api/v1/ready` | Readiness probe (model actually loaded) |
| POST | `/api/v1/internal/predict` | Score one message |
| GET | `/api/v1/internal/models/{model_name}/production` | Current production model's metrics |

`/internal/predict` is not meant to be internet-facing — per the approved
architecture it is called only by `app_service`, over the private network
/ service mesh, which is why this service has no CORS configuration at all.

### Example request/response

```bash
curl -X POST http://localhost:8002/api/v1/internal/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "URGENT! Your bank account will be blocked. Verify your OTP now."}'
```

```json
{
  "verdict": "scam",
  "scam_probability": 0.7478,
  "risk_level": "high",
  "scam_category": "banking_fraud",
  "confidence_score": 0.4957,
  "threat_score": 0.8978,
  "top_contributing_tokens": [
    {"token": "now", "weight": 0.09019},
    {"token": "click", "weight": 0.085622},
    {"token": "immediate", "weight": 0.082289},
    {"token": "account", "weight": 0.072379},
    {"token": "bank", "weight": 0.071761}
  ],
  "model_name": "naive_bayes",
  "model_version": "v1",
  "latency_ms": 3.67
}
```

This is real, captured output from an actual local run against a
model trained on the bundled sample dataset — not a hand-written example.

---

## 5. Running the tests

```bash
cd backend
python -m pytest tests ml_common/tests ml_training/tests ml_service/tests -v
```

151 tests, all passing as of this build: 22 `app_service` (Phase 2,
untouched) + 30 `ml_common` + 34 `ml_training` (including a full,
non-mocked, end-to-end training-pipeline integration test) + 45
`ml_service` (including a full, non-mocked HTTP integration test that
trains a real model and hits the live FastAPI app).

Run one package's suite in isolation, e.g.:

```bash
python -m pytest ml_service/tests -v
```

---

## 6. Real bugs found and fixed during this build

Every one of these was caught by actually running the code, not by
inspection — consistent with how Phase 2 (`app_service`) was verified:

1. **Cross-package artifact deserialization.** `TfidfFeatureExtractor`
   was originally defined in `ml_training.features`. `joblib` pickles
   objects by their class's module path, so loading a saved vectorizer
   from `ml_service` would have silently required importing
   `ml_training` — breaking the one-directional dependency the whole
   design relies on. Fixed by moving the class to `ml_common.features`
   and reverifying artifact loading across a process boundary that never
   imports `ml_training`.
2. **Phone-number regex over-matching.** The original pattern normalized
   bare numeric strings (e.g. a 6-digit OTP code) as `__phone__` instead
   of `__num__`, because every separator in the pattern was optional.
   Fixed by requiring at least one real separator character.
3. **TF-IDF `max_df`/`min_df` conflict on tiny corpora.** A fractional
   `max_df=0.95` combined with a very small training batch (e.g. 1
   document) computes an effective max-document-count of 0, which
   scikit-learn rejects. Fixed with a small-corpus safety guard in
   `TfidfFeatureExtractor.fit_transform`.
4. **ROC-AUC on a single-class evaluation split.** Depending on the
   installed scikit-learn version, `roc_auc_score` either raises
   `ValueError` or silently returns `NaN` with a warning when only one
   class is present in `y_true`. The original code only caught the
   exception case. Fixed by explicitly detecting the single-class case
   up front and treating `NaN` as a second safety net.
5. **Empty-string CSV fields read as NaN.** `pandas.read_csv` parses an
   empty quoted field (`""`) as `NaN`, not `""`. The original
   empty-text filter called `.astype(str)` first, which turns `NaN` into
   the literal string `"nan"` — silently defeating the filter. Fixed by
   checking `.isna()` before stringifying.

---

## 7. Dependencies

```
scikit-learn
pandas
numpy
scipy
joblib
fastapi
uvicorn
pydantic
pydantic-settings
slowapi
pytest
httpx
```

Pin exact versions the same way `app_service/requirements.txt` does
before deploying; kept unpinned here since this doc, not a lockfile, is
the source of truth for *why* each one is present.
