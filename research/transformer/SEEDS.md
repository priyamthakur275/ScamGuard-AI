# Transformer runs over three seeds

Seed 42: `backend/ml_training/research/transformer_results.json` (full results).
Seeds 123 and 2026: run with `--seed 123` / `--seed 2026` on a Colab T4 from the same code (commit 7b76b04). The
Colab runtime ended before their JSON files were copied out, so `seeds_summary.csv` holds the values transcribed
from the notebook's printed output (F1 of the transformer alone, F1 and false-alarm rate with the risk engine).
LR v2 is deterministic and identical across seeds; its false-alarm rates are from transformer_results.json.
