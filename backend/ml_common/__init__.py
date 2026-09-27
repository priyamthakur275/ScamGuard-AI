"""Shared library used by both the offline training pipeline (ml_training)
and the online inference service (ml_service).

Housing preprocessing and the model registry here -- instead of duplicating
them in both services -- is what guarantees train/serve parity: the exact
same cleaning, tokenization, and artifact-loading code runs at training
time and at prediction time.
"""
