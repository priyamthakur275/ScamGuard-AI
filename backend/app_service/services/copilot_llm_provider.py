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


_PROVIDERS: dict[str, type[CopilotLlmProvider]] = {}


def get_llm_answer(question: str, grounding_context: str) -> str:
    settings = get_settings()
    provider_name = getattr(settings, "COPILOT_LLM_PROVIDER", None)

    if not provider_name:
        raise CopilotLlmUnavailableError(
            "No LLM provider is configured for Copilot. Using the deterministic, "
            "evidence-grounded assistant instead."
        )

    provider_cls = _PROVIDERS.get(provider_name)
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
