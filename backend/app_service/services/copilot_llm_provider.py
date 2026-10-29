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
    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        """Send one system + user turn and return the model's text. Must raise
        on any HTTP or format failure; must never return a fabricated answer."""

    def stream(self, system: str, user: str, max_tokens: int = 400):
        """Yield the answer in pieces as the model writes it. Providers without
        streaming yield the whole answer once."""
        yield self.complete(system, user, max_tokens)

    def answer(self, question: str, grounding_context: str) -> str:
        """grounding_context is a plain-text rendering of ONLY the real,
        already-computed evidence for this scan -- no other knowledge source
        is given to the model."""
        return self.complete(SYSTEM_PROMPT, _user_prompt(question, grounding_context))


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

    # Thinking models can take a while before the first token.
    return httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))


def _gemini_config(model: str, max_tokens: int) -> dict:
    """Gemini 2.x turns thinking off with thinkingBudget=0. Gemini 3.x has no
    'off' and counts thinking tokens against maxOutputTokens, so it gets a low
    thinking level and extra room, or the visible answer can come back empty."""
    if model.startswith("gemini-2"):
        return {"maxOutputTokens": max_tokens, "temperature": 0.3, "thinkingConfig": {"thinkingBudget": 0}}
    return {"maxOutputTokens": max_tokens + 1024, "temperature": 0.3, "thinkingConfig": {"thinkingLevel": _THINKING_LEVEL[0]}}


# "minimal" is the fastest Gemini 3 setting; models that reject it fall back to
# "low" once, and the choice is remembered for the rest of the process.
_THINKING_LEVEL = ["minimal"]


def _downgrade_thinking(status: int, body: str) -> bool:
    if status == 400 and _THINKING_LEVEL[0] == "minimal" and "thinking" in body.lower():
        _THINKING_LEVEL[0] = "low"
        return True
    return False


class GeminiProvider(CopilotLlmProvider):
    """Google Gemini (has a free tier). COPILOT_LLM_PROVIDER=gemini."""

    default_model = "gemini-3.5-flash-lite"

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        settings = get_settings()
        model = settings.COPILOT_LLM_MODEL or self.default_model
        with _http_client() as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": settings.COPILOT_LLM_API_KEY},
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": _gemini_config(model, max_tokens),
                },
            )
            if _downgrade_thinking(resp.status_code, resp.text):
                return self.complete(system, user, max_tokens)
            resp.raise_for_status()
            parts = resp.json()["candidates"][0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()


    def stream(self, system: str, user: str, max_tokens: int = 400):
        import json as _json

        settings = get_settings()
        model = settings.COPILOT_LLM_MODEL or self.default_model
        with _http_client() as client, client.stream(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse",
            headers={"x-goog-api-key": settings.COPILOT_LLM_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": _gemini_config(model, max_tokens),
            },
        ) as resp:
            if resp.status_code == 400 and _downgrade_thinking(400, resp.read().decode("utf-8", "replace")):
                yield from self.stream(system, user, max_tokens)
                return
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = _json.loads(line[5:])
                for cand in chunk.get("candidates", [])[:1]:
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("text"):
                            yield part["text"]


class AnthropicProvider(CopilotLlmProvider):
    """Anthropic API. COPILOT_LLM_PROVIDER=anthropic; set COPILOT_LLM_MODEL."""

    default_model = ""

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
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
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            resp.raise_for_status()
            return "".join(b.get("text", "") for b in resp.json()["content"] if b.get("type") == "text").strip()


class OpenAIProvider(CopilotLlmProvider):
    """OpenAI-compatible chat completions. COPILOT_LLM_PROVIDER=openai."""

    default_model = "gpt-4o-mini"
    base_url = "https://api.openai.com/v1"

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        settings = get_settings()
        with _http_client() as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.COPILOT_LLM_API_KEY}"},
                json={
                    "model": settings.COPILOT_LLM_MODEL or self.default_model,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()


    def stream(self, system: str, user: str, max_tokens: int = 400):
        import json as _json

        settings = get_settings()
        with _http_client() as client, client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.COPILOT_LLM_API_KEY}"},
            json={
                "model": settings.COPILOT_LLM_MODEL or self.default_model,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "stream": True,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:") or line.strip() == "data: [DONE]":
                    continue
                delta = _json.loads(line[5:])["choices"][0].get("delta", {}).get("content")
                if delta:
                    yield delta


class GroqProvider(OpenAIProvider):
    """Groq (free tier, OpenAI-compatible). COPILOT_LLM_PROVIDER=groq."""

    default_model = "llama-3.3-70b-versatile"
    base_url = "https://api.groq.com/openai/v1"


_PROVIDERS: dict[str, type[CopilotLlmProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def get_configured_provider() -> CopilotLlmProvider:
    """Return the configured provider or raise CopilotLlmUnavailableError."""
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

    return provider_cls()


def get_llm_answer(question: str, grounding_context: str) -> str:
    return get_configured_provider().answer(question, grounding_context)


def get_llm_completion(system: str, user: str, max_tokens: int = 600) -> str:
    return get_configured_provider().complete(system, user, max_tokens)


def self_check() -> str:
    """One tiny request to the configured provider; returns a log line that
    says whether it works. Never includes the API key."""
    try:
        provider = get_configured_provider()
    except CopilotLlmUnavailableError as exc:
        return f"Copilot LLM not configured: {exc}"
    name = type(provider).__name__
    try:
        import time as _time

        started = _time.monotonic()
        reply = provider.complete("Reply with the single word OK.", "ping", max_tokens=20)
        took = _time.monotonic() - started
        if not reply.strip():
            return f"Copilot LLM check FAILED ({name}): empty reply after {took:.1f}s"
        return f"Copilot LLM check OK ({name}): replied {reply[:20]!r} in {took:.1f}s"
    except Exception as exc:  # noqa: BLE001 - report any failure in the log
        detail = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                detail = f" HTTP {resp.status_code}: {resp.json().get('error', {}).get('message', '')[:200]}"
            except Exception:  # noqa: BLE001
                detail = f" HTTP {resp.status_code}"
        return f"Copilot LLM check FAILED ({name}): {type(exc).__name__}{detail}"
