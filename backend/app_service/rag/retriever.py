"""Hybrid retriever over ScamGuard's curated scam knowledge base.

Three independent signals are combined for every knowledge-base entry:

* vector similarity: cosine similarity of character n-gram TF-IDF vectors
  (3 to 5 characters inside word boundaries). Character n-grams survive the
  misspellings, number swaps and Hinglish spellings that scam messages use,
  and need no external embedding service or model download;
* keyword match: the IDF-weighted share of the query's content words that
  also appear in the entry (a normalised form of BM25-style lexical match);
* tactic overlap: how much of the entry's known scam pattern (its tactics,
  using the same intent ids as the Scam X-Ray) is present in the query.

relevance = 0.45 * vector + 0.25 * keyword + 0.30 * tactic, in [0, 1].

Entries are of two kinds. "scam" entries are known fraud patterns and become
citations. "genuine" entries are the usual formats of real bank, payment and
service messages; they carry no tactics, so their relevance is the vector and
keyword part rescaled to [0, 1] and halved when the query shows any scam
tactic (a copied alert format that also asks for something is not genuine).
"""
from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_PATH = Path(__file__).with_name("knowledge_base.json")

W_VECTOR = 0.45
W_KEYWORD = 0.25
W_TACTIC = 0.30

_REQUIRED_FIELDS = ("id", "scam_type", "title", "transcript_body", "what_happens_next", "source_name", "source_url")
KINDS = ("scam", "genuine")

_STOPWORDS = frozenset(
    """a an the and or but if of to in on at by for with from is are was were be been being this that these those it its
    you your yours we our us i me my he she they them their his her hi hello dear sir madam please pls kindly will shall can
    could would should may might must do does did done have has had not no yes as so than then there here what which who whom
    how when where why all any some more most other into over under again just also only very too up down out about above below
    hai hain ka ki ke ko se me mein aap aapka aapke aapki main mera meri tum yeh ye woh wo kar karo kare raha rahe rahi tha thi
    hoga hogi hoon hu ho""".split()
)
_WORD_RX = re.compile(r"[a-z0-9]+")


def _content_words(text: str) -> list[str]:
    return [w for w in _WORD_RX.findall(text.lower()) if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()]


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    kind: str
    scam_type: str
    title: str
    transcript_body: str
    tactics: tuple[str, ...]
    what_happens_next: str
    source_name: str
    source_url: str


@dataclass(frozen=True)
class RetrievedEntry:
    entry: KnowledgeEntry
    relevance: float
    vector_score: float
    keyword_score: float
    tactic_score: float
    shared_tactics: tuple[str, ...]


def load_knowledge_base(path: Path = KB_PATH) -> list[KnowledgeEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{path.name} must be a non-empty JSON list")
    entries: list[KnowledgeEntry] = []
    seen: set[str] = set()
    for item in raw:
        missing = [f for f in _REQUIRED_FIELDS if not item.get(f)]
        if missing:
            raise ValueError(f"knowledge base entry {item.get('id', '?')} is missing {missing}")
        kind = item.get("kind", "scam")
        if kind not in KINDS:
            raise ValueError(f"knowledge base entry {item['id']} has unknown kind {kind!r}")
        if kind == "scam" and not item.get("tactics"):
            raise ValueError(f"scam entry {item['id']} must list its tactics")
        if item["id"] in seen:
            raise ValueError(f"duplicate knowledge base id {item['id']}")
        if not str(item["source_url"]).startswith("https://"):
            raise ValueError(f"knowledge base entry {item['id']} must cite an https source")
        seen.add(item["id"])
        entries.append(
            KnowledgeEntry(
                id=item["id"],
                kind=kind,
                scam_type=item["scam_type"],
                title=item["title"],
                transcript_body=item["transcript_body"],
                tactics=tuple(item.get("tactics") or ()),
                what_happens_next=item["what_happens_next"],
                source_name=item["source_name"],
                source_url=item["source_url"],
            )
        )
    return entries


class HybridRetriever:
    def __init__(self, entries: list[KnowledgeEntry]):
        if not entries:
            raise ValueError("HybridRetriever needs at least one entry")
        self.entries = entries
        docs = [f"{e.title}. {e.transcript_body}" for e in entries]
        self._vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True)
        self._doc_matrix = self._vectorizer.fit_transform(docs)
        self._doc_words = [set(_content_words(d)) for d in docs]
        n = len(docs)
        df: dict[str, int] = {}
        for words in self._doc_words:
            for w in words:
                df[w] = df.get(w, 0) + 1
        self._idf = {w: math.log((1 + n) / (1 + c)) + 1.0 for w, c in df.items()}
        self._unknown_idf = math.log(1 + n) + 1.0

    def _keyword_scores(self, query: str) -> list[float]:
        terms = set(_content_words(query))
        if not terms:
            return [0.0] * len(self.entries)
        total = sum(self._idf.get(t, self._unknown_idf) for t in terms)
        scores = []
        for words in self._doc_words:
            hit = sum(self._idf[t] for t in terms if t in words)
            scores.append(min(1.0, 2.0 * hit / total))
        return scores

    def search(self, query: str, query_tactics: set[str], top_k: int = 5, kind: str = "scam") -> list[RetrievedEntry]:
        if not query.strip():
            return []
        vec = cosine_similarity(self._vectorizer.transform([query]), self._doc_matrix)[0]
        kw = self._keyword_scores(query)
        results: list[RetrievedEntry] = []
        for i, entry in enumerate(self.entries):
            if entry.kind != kind:
                continue
            shared = tuple(t for t in entry.tactics if t in query_tactics)
            tactic = len(shared) / len(entry.tactics) if entry.tactics else 0.0
            v = float(max(0.0, min(1.0, vec[i])))
            if entry.kind == "genuine":
                relevance = (W_VECTOR * v + W_KEYWORD * kw[i]) / (W_VECTOR + W_KEYWORD)
                if query_tactics:
                    relevance *= 0.5
            else:
                relevance = W_VECTOR * v + W_KEYWORD * kw[i] + W_TACTIC * tactic
            results.append(RetrievedEntry(entry, round(relevance, 4), round(v, 4), round(kw[i], 4), round(tactic, 4), shared))
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:top_k]


_retriever: HybridRetriever | None = None
_lock = threading.Lock()


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        with _lock:
            if _retriever is None:
                _retriever = HybridRetriever(load_knowledge_base())
    return _retriever
