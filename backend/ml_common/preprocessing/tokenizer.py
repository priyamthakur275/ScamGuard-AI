"""Tokenization and lexical normalization.

Deliberate design decision: we do NOT depend on NLTK's runtime corpus
download (`nltk.download(...)`) for stopwords, because that makes model
training and, worse, service startup dependent on reaching an external
server at an unpredictable time. Instead we bundle a fixed, versioned
English stopword list and a small rule-based suffix stemmer. This trades
a little linguistic sophistication for full reproducibility and offline
reliability -- the right trade for a production inference path.
"""
import re
from dataclasses import dataclass, field

_TOKEN_PATTERN = re.compile(r"[a-zA-Z_]+")

# A standard, fixed English stopword list (bundled, not downloaded at
# runtime). Kept intentionally close to the classic SMART/NLTK list.
ENGLISH_STOPWORDS: frozenset[str] = frozenset(
    """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further had hadn't has hasn't have haven't having he he'd he'll
    he's her here here's hers herself him himself his how how's i i'd i'll
    i'm i've if in into is isn't it it's its itself let's me more most
    mustn't my myself no nor not of off on once only or other ought our
    ours ourselves out over own same shan't she she'd she'll she's should
    shouldn't so some such than that that's the their theirs them
    themselves then there there's these they they'd they'll they're
    they've this those through to too under until up very was wasn't we
    we'd we'll we're we've were weren't what what's when when's where
    where's which while who who's whom why why's with won't would
    wouldn't you you'd you'll you're you've your yours yourself yourselves
    """.split()
)

# Preserved because they carry strong signal for scam/urgency detection --
# removing them would throw away exactly the linguistic cues the system
# is meant to detect (per the approved architecture's "urgency indicators"
# and "social engineering behaviour" feature goals).
_PRESERVED_TOKENS: frozenset[str] = frozenset(
    {"not", "no", "now", "urgent", "immediately", "free", "win", "won"}
)

_EFFECTIVE_STOPWORDS: frozenset[str] = ENGLISH_STOPWORDS - _PRESERVED_TOKENS

_SUFFIXES: tuple[str, ...] = ("ational", "tional", "ing", "edly", "ed", "ly", "es", "s")


def _simple_stem(token: str) -> str:
    """A conservative Porter-like suffix stripper.

    Not a full Porter Stemmer implementation, but sufficient (and fully
    deterministic, dependency-free) for TF-IDF feature reduction, which
    only needs *consistent* collapsing of morphological variants, not
    linguistically perfect stems.
    """
    if len(token) <= 4:
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


@dataclass(frozen=True)
class TokenizerConfig:
    remove_stopwords: bool = True
    apply_stemming: bool = True
    min_token_length: int = 2
    stopwords: frozenset[str] = field(default_factory=lambda: _EFFECTIVE_STOPWORDS)


class Tokenizer:
    """Splits normalized text into a list of model-ready tokens."""

    def __init__(self, config: TokenizerConfig | None = None):
        self._config = config or TokenizerConfig()

    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []

        raw_tokens = _TOKEN_PATTERN.findall(text)
        tokens: list[str] = []

        for token in raw_tokens:
            if len(token) < self._config.min_token_length:
                continue
            if self._config.remove_stopwords and token in self._config.stopwords:
                continue
            if self._config.apply_stemming:
                token = _simple_stem(token)
            if token:
                tokens.append(token)

        return tokens

    def tokenize_to_string(self, text: str) -> str:
        """Convenience method returning space-joined tokens, which is the
        input format scikit-learn's TfidfVectorizer expects when a custom
        `preprocessor`/`tokenizer` pair is not wired in directly.
        """
        return " ".join(self.tokenize(text))
