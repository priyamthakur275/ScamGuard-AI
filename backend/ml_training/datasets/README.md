# Training datasets

The production model (v4) is trained on **ScamGuard-IN-2026**, a corpus of Indian SMS
built for this project. Details, sources, licences, the label audit and limitations are in
[`scamguard_in_2026/DATASHEET.md`](scamguard_in_2026/DATASHEET.md).

| File | What it is |
|---|---|
| `scamguard_in_2026/scamguard_in_2026.csv` | The corpus: `text, label, source, subtype, is_synthetic, campaign, split` |
| `scamguard_in_2026/build.py` | Rebuilds the corpus from its sources (deterministic) |
| `scamguard_in_2026/imc_audit.csv`, `india_sms_audit.csv`, `label_corrections.csv` | Every label decision of the audit |
| `scamguard_in_2026/advisories_2025_26.csv` | Scam texts quoted in 2025-26 advisories (test only) |
| `scamguard_in_2026/synthetic.py` | Synthetic templates (train only) |
| `indian_challenge_set.csv`, `indian_challenge_set_b.csv` | Hand-written development sets used while designing the intent rules |
| `sample_messages.csv` | 24 hand-written messages used by the pipeline tests |

Rebuild and train:

```bash
cd backend
bash ml_training/datasets/scamguard_in_2026/fetch_sources.sh     # public raw sources
python -m ml_training.datasets.scamguard_in_2026.build          # corpus
python -m ml_training.research.train_production                 # model v4 (registered and promoted)
python -m ml_training.research.run_experiments                  # every number in the paper
```

Team SMS exports go in `scamguard_in_2026/raw/team/` (SMS Backup & Restore XML, or one
message per line in a .txt; a file name containing "scam" marks scam messages). They are
masked by `pii.py`, written to `team_2026.csv` for review, and used only as the 2026 test set.
