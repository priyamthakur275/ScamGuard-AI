"""Mask personal data in contributed SMS before they are stored or committed.

Keeps the message shape (an OTP still looks like a 6-digit code, an amount still
looks like an amount) so the model sees realistic text, but no real value survives.
"""

from __future__ import annotations

import random
import re

_R = random.Random(7)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_VPA = re.compile(r"\b[\w.-]{2,}@(ok\w+|ybl|ibl|axl|paytm|upi|apl|yapl|ptyes|ptsbi|pthdfc|icici|sbi|hdfc\w*|kotak|axis\w*)\b", re.I)
_MOBILE = re.compile(r"(?<!\d)(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_CARD_OR_ACCT = re.compile(r"(?<![\dX*])\d{9,18}(?!\d)")
_MASKED_ACCT = re.compile(r"((?:a/c|acct|account|card)[^\d]{0,12}(?:no\.?\s*)?[Xx*.]{1,6})\d{3,4}", re.I)
_SHORT_NUM = re.compile(r"(?<![\d.,])\d{4,8}(?![\d.,])")
_NAME_AFTER = re.compile(r"\b(Dear|Hi|Hello|Mr\.?|Ms\.?|Mrs\.?)\s+([A-Z][a-z]{2,})(\s+[A-Z][a-z]{2,})?")
_PLACEHOLDER_NAMES = ["Customer", "Rahul", "Priya", "Amit", "Sneha", "Arjun"]


def _digits(n: int) -> str:
    return "".join(_R.choice("0123456789") for _ in range(n))


def mask_pii(text: str) -> str:
    t = text
    t = _EMAIL.sub("user@mail.example", t)
    t = _VPA.sub(lambda m: "user" + _digits(2) + "@" + m.group(1), t)
    t = _MOBILE.sub(lambda m: "9" + _digits(9), t)
    t = _MASKED_ACCT.sub(lambda m: m.group(1) + _digits(4), t)
    t = _CARD_OR_ACCT.sub(lambda m: _digits(len(m.group(0))), t)
    t = _SHORT_NUM.sub(lambda m: _digits(len(m.group(0))), t)  # OTPs, PINs, short refs
    t = _NAME_AFTER.sub(lambda m: m.group(1) + " " + _R.choice(_PLACEHOLDER_NAMES), t)
    return t
