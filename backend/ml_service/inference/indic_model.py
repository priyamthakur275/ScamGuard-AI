"""Optional second model for Hindi and Hinglish messages (v2).

On 77 real Hindi messages the TF-IDF model scores 64.7% F1; a fine-tuned XLM-R scores 84.5 +/- 4.2
over three seeds (research/transformer/SEEDS.md). This module serves a compact copy of that model
(vocabulary trimmed to the training text, int8 ONNX; see ml_training/research/xlmr_compact.py)
with onnxruntime and the `tokenizers` library only, no PyTorch.

It is OFF unless INDIC_MODEL_DIR points to a folder holding model.int8.onnx, tokenizer.json and
vocab_map.npy, or INDIC_MODEL_URL points to a zip of those files (downloaded once at first use).
When it is off, or fails to load, scoring falls back to the TF-IDF model with no change.
"""
from __future__ import annotations

import io
import logging
import os
import threading
import urllib.request
import zipfile

import numpy as np

from ml_common.preprocessing.multilingual import detect_language

logger = logging.getLogger(__name__)
MAX_LEN = 128
MODEL_NAME = "xlmr-indic-int8"


def is_indic(text: str) -> bool:
    """Hindi in Devanagari, or Hinglish as the dataset's detector sees it."""
    if not text:
        return False
    if sum(1 for c in text if "ऀ" <= c <= "ॿ") >= 3:
        return True
    return detect_language(text)[0] in ("hindi", "hinglish", "mixed")


class IndicModel:
    def __init__(self, folder: str):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        self._session = ort.InferenceSession(os.path.join(folder, "model.int8.onnx"), so, providers=["CPUExecutionProvider"])
        self._inputs = {i.name for i in self._session.get_inputs()}
        self._tok = Tokenizer.from_file(os.path.join(folder, "tokenizer.json"))
        self._tok.enable_truncation(MAX_LEN)
        self._vmap = np.load(os.path.join(folder, "vocab_map.npy"))

    def probability(self, text: str) -> float:
        enc = self._tok.encode(text)
        ids = self._vmap[np.asarray([enc.ids], dtype=np.int64)]
        feed = {"input_ids": ids, "attention_mask": np.asarray([enc.attention_mask], dtype=np.int64)}
        if "token_type_ids" in self._inputs:
            feed["token_type_ids"] = np.zeros_like(ids)
        logits = self._session.run(None, feed)[0][0].astype(np.float64)
        e = np.exp(logits - logits.max())
        return float(e[1] / e.sum())


_lock = threading.Lock()
_model: IndicModel | None = None
_tried = False


def _download(url: str) -> str:
    dest = os.path.join(os.environ.get("TMPDIR", "/tmp"), "scamguard_indic_model")
    if not os.path.exists(os.path.join(dest, "model.int8.onnx")):
        os.makedirs(dest, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 - URL comes from deployment config
            zipfile.ZipFile(io.BytesIO(r.read())).extractall(dest)
    return dest


def get_indic_model() -> IndicModel | None:
    """The loaded model, or None when it is not configured or cannot load. Loads at most once."""
    global _model, _tried
    if _tried:
        return _model
    with _lock:
        if _tried:
            return _model
        _tried = True
        folder, url = os.environ.get("INDIC_MODEL_DIR", ""), os.environ.get("INDIC_MODEL_URL", "")
        if not folder and not url:
            return None
        try:
            _model = IndicModel(folder or _download(url))
            logger.info("Indic model loaded")
        except Exception:
            logger.exception("Indic model could not be loaded; using the TF-IDF model for all messages")
            _model = None
        return _model


def reset_for_tests() -> None:
    global _model, _tried
    _model, _tried = None, False
