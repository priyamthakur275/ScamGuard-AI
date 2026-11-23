# Transformer experiment (v2)

`ScamGuard_Transformers_Colab.ipynb` fine-tunes MuRIL and XLM-RoBERTa and compares them with the deployed
TF-IDF + LR system on identical splits. Open it in Google Colab, choose a T4 GPU, and Run all (about 25-40 minutes).

The notebook only runs `backend/ml_training/research/transformer_experiment.py`. A CPU check of the whole
pipeline, with a tiny untrained model and no downloads, runs in about two minutes:

    cd backend && python -m ml_training.research.transformer_experiment --smoke --out /tmp/smoke

Results (`transformer_results.json` / `.md`) are written next to the script. The deployed system stays LR v5
unless a transformer wins on the held-out sets by a statistically significant margin (McNemar) and fits the
latency budget; the two-stage mode (transformer only for messages in LR's 0.3-0.7 review band) is the
intended way to add it.
