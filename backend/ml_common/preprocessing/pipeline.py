"""The NLP Preprocessing Module from the approved High-Level Design
(Section 4.1.1): composes TextCleaner and Tokenizer behind one interface.

Single Responsibility + Composition over inheritance: this class does not
know HOW to clean or tokenize, only that it must run cleaning then
tokenization, in order. Swapping either implementation (e.g. a spaCy-backed
tokenizer) requires no change here -- Open/Closed Principle.
"""
from dataclasses import dataclass

from ml_common.preprocessing.text_cleaner import CleaningConfig, TextCleaner
from ml_common.preprocessing.tokenizer import Tokenizer, TokenizerConfig


@dataclass(frozen=True)
class PreprocessingConfig:
    cleaning: CleaningConfig = None
    tokenizing: TokenizerConfig = None

    def __post_init__(self):
        object.__setattr__(self, "cleaning", self.cleaning or CleaningConfig())
        object.__setattr__(self, "tokenizing", self.tokenizing or TokenizerConfig())


class TextPreprocessingPipeline:
    """The single, canonical text-preprocessing path for this system.

    IMPORTANT: this exact class -- constructed with the exact same config
    -- must be used both when fitting the TF-IDF vectorizer during
    training and when transforming a message at inference time. Divergence
    here (the single most common production ML bug) silently corrupts
    predictions because the vectorizer's vocabulary no longer matches the
    tokens it receives.
    """

    def __init__(self, config: PreprocessingConfig | None = None):
        self._config = config or PreprocessingConfig()
        self._cleaner = TextCleaner(self._config.cleaning)
        self._tokenizer = Tokenizer(self._config.tokenizing)

    def process(self, raw_text: str) -> str:
        """Returns a single space-joined string of processed tokens,
        ready to be handed to a TfidfVectorizer (or any bag-of-words
        style feature extractor).
        """
        cleaned = self._cleaner.clean(raw_text)
        return self._tokenizer.tokenize_to_string(cleaned)

    def process_batch(self, raw_texts: list[str]) -> list[str]:
        return [self.process(text) for text in raw_texts]

    def process_to_tokens(self, raw_text: str) -> list[str]:
        """Returns the token list directly, useful for explainability
        (mapping feature weights back to individual words) rather than
        vectorization.
        """
        cleaned = self._cleaner.clean(raw_text)
        return self._tokenizer.tokenize(cleaned)
