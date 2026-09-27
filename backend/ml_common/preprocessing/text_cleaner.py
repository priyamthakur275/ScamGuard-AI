"""Text normalization utilities.

This module owns exactly one responsibility (SRP): turning a raw, messy
string into a normalized string. It does not tokenize, remove stopwords,
or stem -- that is the tokenizer's job. Keeping these concerns separate
means each can be tested, replaced, or reused independently.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CleaningConfig:
    """Configuration for the text cleaning step.

    Frozen (immutable) so a single config instance can be safely shared
    across threads/processes without risk of accidental mutation.
    """

    lowercase: bool = True
    replace_urls: bool = True
    replace_emails: bool = True
    replace_phone_numbers: bool = True
    replace_numbers: bool = True
    remove_punctuation: bool = True
    collapse_whitespace: bool = True

    url_token: str = " __url__ "
    email_token: str = " __email__ "
    phone_token: str = " __phone__ "
    number_token: str = " __num__ "


_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s])?(?:\(?\d{2,4}\)?[-.\s]){1,4}\d{2,4}\b")
_NUMBER_PATTERN = re.compile(r"\b\d+\b")
_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class TextCleaner:
    """Normalizes raw text into a canonical, model-ready string.

    Replacing URLs/emails/phone numbers/numbers with fixed placeholder
    tokens (rather than deleting them) is a deliberate feature-engineering
    choice: scam messages disproportionately contain these entities, so
    their *presence* remains a signal for TF-IDF even after the specific
    value is normalized away. This also prevents the vocabulary from
    exploding with one-off numbers/URLs that would never generalize.
    """

    def __init__(self, config: CleaningConfig | None = None):
        self._config = config or CleaningConfig()

    def clean(self, text: str) -> str:
        if text is None:
            return ""

        cleaned = text

        if self._config.replace_urls:
            cleaned = _URL_PATTERN.sub(self._config.url_token, cleaned)

        if self._config.replace_emails:
            cleaned = _EMAIL_PATTERN.sub(self._config.email_token, cleaned)

        if self._config.replace_phone_numbers:
            cleaned = _PHONE_PATTERN.sub(self._config.phone_token, cleaned)

        if self._config.lowercase:
            cleaned = cleaned.lower()

        if self._config.remove_punctuation:
            cleaned = _PUNCTUATION_PATTERN.sub(" ", cleaned)

        if self._config.replace_numbers:
            cleaned = _NUMBER_PATTERN.sub(self._config.number_token.strip(), cleaned)

        if self._config.collapse_whitespace:
            cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()

        return cleaned

    def clean_batch(self, texts: list[str]) -> list[str]:
        return [self.clean(text) for text in texts]
