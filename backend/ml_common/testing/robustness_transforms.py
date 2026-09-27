"""Controlled text transformations for robustness testing (Phase 16).

INTERNAL/EVALUATION TOOLING ONLY. Every function here is a pure,
deterministic text transform -- no randomness, no ML, nothing that could
be tuned to make a model "look better". Given the same input, every
transform always produces the same output, so a robustness report is
fully reproducible and auditable.

These transforms are never applied to real user input in the live scan
pipeline -- they exist only to generate controlled variants of a message
for comparing the model's real output before and after, via the exact
same real pipeline (see app_service/services/robustness_service.py).
"""
import re
from dataclasses import dataclass
from typing import Callable

_LEETSPEAK_MAP = str.maketrans({"o": "0", "O": "0", "e": "3", "i": "1", "a": "4", "A": "4", "s": "$"})

# A small, explicit set of Unicode homoglyphs -- visually similar
# characters from other scripts commonly used to spoof Latin letters in
# lookalike domains. Not exhaustive; deliberately small and documented.
_HOMOGLYPH_MAP = str.maketrans({
    "a": "а",  # Cyrillic а (U+0430)
    "e": "е",  # Cyrillic е (U+0435)
    "o": "о",  # Cyrillic о (U+043E)
    "p": "р",  # Cyrillic р (U+0440)
    "c": "с",  # Cyrillic с (U+0441)
})

_URL_PATTERN = re.compile(r"https?://[^\s]+")
_DOMAIN_PATTERN = re.compile(r"(https?://)([^/\s]+)")


@dataclass(frozen=True)
class TextTransform:
    code: str
    label: str
    transformed_text: str


def _case_variation(text: str) -> str:
    return text.upper()


def _whitespace_variation(text: str) -> str:
    words = text.split(" ")
    return "  \t ".join(words).replace(". ", ".\n")


def _punctuation_variation(text: str) -> str:
    result = re.sub(r"!", "!!!", text)
    result = re.sub(r"\b(now|immediately|urgent)\b", r"\1...", result, flags=re.IGNORECASE)
    return result


def _spelling_variation(text: str) -> str:
    return text.translate(_LEETSPEAK_MAP)


def _inserted_symbols(text: str) -> str:
    def spread(match: re.Match) -> str:
        word = match.group(0)
        if len(word) < 4:
            return word
        return ".".join(word)

    return re.sub(r"[A-Za-z]+", spread, text)


def _homoglyph_domain(text: str) -> str:
    def replace_host(match: re.Match) -> str:
        scheme, host = match.group(1), match.group(2)
        return scheme + host.translate(_HOMOGLYPH_MAP)

    return _DOMAIN_PATTERN.sub(replace_host, text)


def _url_obfuscation(text: str) -> str:
    def obfuscate(match: re.Match) -> str:
        url = match.group(0)
        # Percent-encode a '/' WITHIN THE PATH only -- naively replacing
        # the first '/' in the whole URL would corrupt the scheme's own
        # "://" instead of obfuscating anything meaningful.
        scheme_end = url.find("://") + 3
        host_end = url.find("/", scheme_end)
        if host_end == -1:
            return url  # no path to obfuscate
        return url[:host_end] + "%2F" + url[host_end + 1:]

    return _URL_PATTERN.sub(obfuscate, text)


TRANSFORM_CATALOG: tuple[tuple[str, str, Callable[[str], str]], ...] = (
    ("case_change", "Case change (UPPERCASE)", _case_variation),
    ("whitespace", "Irregular whitespace", _whitespace_variation),
    ("punctuation", "Punctuation variation", _punctuation_variation),
    ("spelling_variation", "Leetspeak-style spelling variation", _spelling_variation),
    ("inserted_symbols", "Inserted symbols (keyword-filter evasion)", _inserted_symbols),
    ("homoglyph_domain", "Homoglyph lookalike domain", _homoglyph_domain),
    ("url_obfuscation", "URL obfuscation (percent-encoding)", _url_obfuscation),
)


def apply_all_transforms(base_text: str) -> tuple[TextTransform, ...]:
    return tuple(
        TextTransform(code=code, label=label, transformed_text=fn(base_text))
        for code, label, fn in TRANSFORM_CATALOG
    )
