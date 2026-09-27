"""Lightweight, self-hosted, stateless CAPTCHA.

This is a real, working challenge-response mechanism -- not a simulation.
It is deliberately NOT a claim of parity with a third-party CAPTCHA
service (reCAPTCHA, hCaptcha, Turnstile): those require an external
account and site/secret keys that this environment has no credentials
for, and swapping one in later is a config change, not an architecture
change, since the verification call site below is the only integration
point that would need to change.

Design: a short arithmetic challenge, with the correct answer never sent
to the client. The token embeds an expiry and an HMAC-SHA256 signature of
"answer:expiry" keyed by the app's own SECRET_KEY, so verification needs
no server-side storage (no database row, no cache entry to clean up) --
the token IS the state, and it cannot be forged or replayed past its
expiry without knowing SECRET_KEY. Comparison uses hmac.compare_digest
throughout to avoid timing side-channels.
"""
import base64
import hmac
import hashlib
import random
import time
from dataclasses import dataclass

CAPTCHA_TTL_SECONDS = 5 * 60


@dataclass(frozen=True)
class CaptchaChallenge:
    question: str
    token: str


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_challenge(secret: str) -> CaptchaChallenge:
    a, b = random.randint(1, 9), random.randint(1, 9)
    op = random.choice(["+", "-"])
    answer = a + b if op == "+" else a - b
    question = f"What is {a} {op} {b}?"

    expires_at = int(time.time()) + CAPTCHA_TTL_SECONDS
    signature = _sign(f"{answer}:{expires_at}", secret)
    token = base64.urlsafe_b64encode(f"{expires_at}:{signature}".encode("utf-8")).decode("utf-8")
    return CaptchaChallenge(question=question, token=token)


def verify_answer(token: str, provided_answer: str, secret: str) -> bool:
    """Returns True only if the token is well-formed, unexpired, and the
    provided answer's signature matches what was issued for this token.
    """
    if not token or provided_answer is None:
        return False
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        expires_at_str, signature = decoded.split(":", 1)
        expires_at = int(expires_at_str)
    except Exception:
        return False

    if time.time() > expires_at:
        return False

    try:
        # Normalize e.g. " 7" / "7 " / "+7" to "7" before signing, so
        # harmless whitespace/sign formatting doesn't fail a correct answer.
        normalized_answer = str(int(str(provided_answer).strip()))
    except (ValueError, TypeError):
        return False

    expected_signature = _sign(f"{normalized_answer}:{expires_at}", secret)
    return hmac.compare_digest(signature, expected_signature)
