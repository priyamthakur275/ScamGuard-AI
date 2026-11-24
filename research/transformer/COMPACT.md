# Can XLM-R run on the free CPU server?

Run: `python -m ml_training.research.xlmr_compact` on a Colab T4 (seed 42, commit 78f435b), 24 Nov 2026.
The Colab runtime was disconnected before the int8 ONNX step finished, so only the first two variants were
measured (values transcribed from the notebook output):

| Variant | Real test F1 / FPR | Real Hindi F1 / FPR |
|---|---|---|
| XLM-R, full, fp32 | 97.27 / 2.26% | 85.29 / 9.52% |
| XLM-R, vocabulary trimmed to training tokens, fp32 | 97.23 / 2.26% | 78.69 / 4.76% |

Finding: trimming the vocabulary to tokens seen in training keeps English accuracy but costs 6.6 F1 points on
real Hindi, because real messages contain tokens the (mostly synthetic) Hindi training text never had. Trimming is
therefore not a free way to fit the model on a small server.

Not measured: int8 size and CPU latency. The full model has about 278M parameters (about 1.1 GB in fp32; int8 would
be roughly a quarter of that), which does not fit Render's free 512 MB instance next to the app.

Deployment options, in order of cost:
1. Keep LR v5 for everything (current state).
2. Full XLM-R, int8, on a 2 GB instance, used only for messages `is_indic()` selects
   (code ready: ml_service/inference/indic_model.py, switched on by INDIC_MODEL_DIR or INDIC_MODEL_URL).
3. Trim with a vocabulary built from a large Hindi corpus instead of the training text, then re-measure.
