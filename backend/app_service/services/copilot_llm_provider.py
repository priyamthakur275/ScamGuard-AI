"""Optional external LLM provider for ScamGuard Copilot.

HONESTY NOTE, same pattern as voice_transcription.py (Phase 6): no
provider is wired up by default. Integrating a real LLM API (OpenAI,
Anthropic, etc.) that this environment has no credentials to test against
would mean either faking success or shipping unverified code -- neither
is acceptable. This module defines the clean integration point (a
provider interface + environment-variable configuration) and a
CopilotLlmUnavailableError that the Copilot service catches to fall back
to the deterministic, evidence-grounded engine (copilot_service.py),
which is the actually-working, actually-tested default path.

To wire in a real provider later: implement CopilotLlmProvider below,
register it in _PROVIDERS, and set COPILOT_LLM_PROVIDER +
COPILOT_LLM_API_KEY. The grounding contract does not change: whatever
provider is used, it must be given ONLY the scan's real evidence as
context and instructed never to state anything not present in it --
enforced by copilot_service.py building the prompt, not by this module.
"""
from abc import ABC, abstractmethod

from app_service.core.config import get_settings


class CopilotLlmUnavailableError(Exception):
    """Raised when an LLM-backed answer was attempted but no provider is
    configured. This is the honest, user-facing state -- the deterministic
    evidence-grounded assistant is what actually answers instead.
    """


class CopilotLlmProvider(ABC):
    @abstractmethod
    def answer(self, question: str, grounding_context: str) -> str:
        """grounding_context is a plain-text rendering of ONLY the real,
        already-computed evidence for this scan -- implementors must not
        add any other knowledge source. Must raise on failure; must never
        return a fabricated answer."""


SYSTEM_PROMPT = (
    "You are ScamGuard's assistant for people in India who received a suspicious message. "
    "Answer ONLY from the scan evidence provided; if the evidence doesn't cover the question, say so. "
    "Use simple, calm language, at most 120 words. Reply in the same language as the question "
    "(English, Hindi or Hinglish). Never ask the user for OTPs, PINs, passwords or card details. "
    "When money was lost, tell them to call 1930 and report at cybercrime.gov.in; for unwanted scam "
    "messages without loss, Chakshu (sancharsaathi.gov.in/sfc)."
)


def _user_prompt(question: str, grounding_context: str) -> str:
    return f"Scan evidence:\n{grounding_context}\n\nUser question: {question}"


def _http_client():
    import httpx

    return httpx.Client(timeout=20.0)


class GeminiProvider(CopilotLlmProvider):
    """Google Gemini (has a free tier). COPILOT_LLM_PROVIDER=gemini."""

    default_model = "gemini-2.5-flash"

    def answer(self, question: str, grounding_context: str) -> str:
        settings = get_settings()
        model = settings.COPILOT_LLM_MODEL or self.default_model
        with _http_client() as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": settings.COPILOT_LLM_API_KEY},
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": _user_prompt(question, grounding_context)}]}],
                    "generationConfig": {"maxOutputTokens": 400, "temperature": 0.2},
                },
            )
            resp.raise_for_status()
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()


class AnthropicProvider(CopilotLlmProvider):
    """Anthropic API. COPILOT_LLM_PROVIDER=anthropic; set COPILOT_LLM_MODEL."""

    default_model = ""

    def answer(self, question: str, grounding_context: str) -> str:
        settings = get_settings()
        with _http_client() as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.COPILOT_LLM_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.COPILOT_LLM_MODEL or self.default_model,
                    "max_tokens": 400,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": _user_prompt(question, grounding_context)}],
                },
            )
            resp.raise_for_status()
            return "".join(b.get("text", "") for b in resp.json()["content"] if b.get("type") == "text").strip()


class OpenAIProvider(CopilotLlmProvider):
    """OpenAI-compatible chat completions. COPILOT_LLM_PROVIDER=openai."""

    default_model = "gpt-4o-mini"

    def answer(self, question: str, grounding_context: str) -> str:
        settings = get_settings()
        with _http_client() as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.COPILOT_LLM_API_KEY}"},
                json={
                    "model": settings.COPILOT_LLM_MODEL or self.default_model,
                    "max_tokens": 400,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _user_prompt(question, grounding_context)},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()


_PROVIDERS: dict[str, type[CopilotLlmProvider]] = {
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def get_llm_answer(question: str, grounding_context: str) -> str:
    settings = get_settings()
    provider_name = getattr(settings, "COPILOT_LLM_PROVIDER", None)

    if not provider_name:
        raise CopilotLlmUnavailableError(
            "No LLM provider is configured for Copilot. Using the deterministic, "
            "evidence-grounded assistant instead."
        )

    provider_cls = _PROVIDERS.get(provider_name.strip().lower())
    if provider_cls is None:
        raise CopilotLlmUnavailableError(
            f"COPILOT_LLM_PROVIDER is set to '{provider_name}', which is not a "
            "recognized/implemented provider."
        )

    api_key = getattr(settings, "COPILOT_LLM_API_KEY", None)
    if not api_key:
        raise CopilotLlmUnavailableError(
            f"LLM provider '{provider_name}' is selected but no COPILOT_LLM_API_KEY is configured."
        )

    provider = provider_cls()
    return provider.answer(question, grounding_context)
