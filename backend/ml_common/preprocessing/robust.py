"""Undo common evasion tricks before a message is scored (v2).

Scammers disguise trigger words so filters miss them: lookalike letters from
other alphabets ("KYС" with a Cyrillic С), zero-width characters inside words,
letters spaced out ("c l i c k"), digits for letters ("cl1ck", "0TP") and
"defanged" links ("hxxp://", "site[.]com", "site dot com"). ``deobfuscate``
maps these back to plain text. It is deterministic, never translates, and
leaves Devanagari untouched.

It is applied once, before both the classifier and the intent rules, so the
model and the rules see the same text.
"""

from __future__ import annotations

import re
import unicodedata

# Cyrillic and Greek letters that look like Latin ones.
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ӏ": "l", "һ": "h",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "І": "I", "Ү": "Y",
    "α": "a", "ε": "e", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "ν": "v", "κ": "k", "ι": "i",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Χ": "X", "Υ": "Y",
})
_ZERO_WIDTH = re.compile(r"[​‌‍⁠﻿­]")
# Five or more single letters separated by one space/dot/dash: "c l i c k", "K.Y.C" needs 3.
_SPACED = re.compile(r"(?<![\w])((?:[A-Za-z][ .\-_*]){2,}[A-Za-z])(?![\w])")
_LEET_WORD = re.compile(r"\b(?=[a-z0-9@$]*[a-z])(?=[a-z0-9@$]*[0-9@$])[a-z0-9@$]{3,}\b", re.IGNORECASE)
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_DEFANG = [(re.compile(r"\bhxxps?\b", re.I), lambda m: m.group(0).lower().replace("xx", "tt")),
           (re.compile(r"\s*\[\s*\.\s*\]\s*|\s*\(\s*\.\s*\)\s*|\s*\{\s*\.\s*\}\s*"), lambda m: "."),
           (re.compile(r"(?<=\w)\s*[\[(]\s*dot\s*[\])]\s*(?=\w)", re.I), lambda m: "."),
           (re.compile(r"(?<=[a-z0-9])\s+dot\s+(?=(?:com|in|ly|xyz|top|co|net|org|me|site|online|click|vip|live|info)\b)", re.I), lambda m: ".")]
# Leet words that are real tokens and must stay: units, codes, short forms.
_KEEP = re.compile(r"^(?:\d{2,}[a-z]{1,3}|\d(?:st|nd|rd|th|g|am|pm|k|kg|gb|mb|x)|[a-z]{1,3}\d+|[a-z]+\d{2,}|\d{2,}[a-z]+|[a-z]*\d{3,}[a-z]*|4g|5g|2fa|b2b|p2p)$", re.I)


def _unleet(m: re.Match) -> str:
    w = m.group(0)
    if _KEEP.match(w):
        return w
    letters = sum(c.isalpha() for c in w)
    return w.translate(_LEET) if letters >= len(w) / 2 else w


def deobfuscate(text: str) -> str:
    if not text:
        return text
    t = unicodedata.normalize("NFKC", text)  # full-width letters, ligatures, styled math letters
    t = _ZERO_WIDTH.sub("", t)
    t = t.translate(_HOMOGLYPHS)
    for rx, fn in _DEFANG:
        t = rx.sub(fn, t)
    t = _SPACED.sub(lambda m: re.sub(r"[ .\-_*]", "", m.group(1)), t)
    t = _LEET_WORD.sub(_unleet, t)
    return t
