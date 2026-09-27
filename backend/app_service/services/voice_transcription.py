"""Server-side audio-file transcription, via an optional, pluggable
external provider.

HONESTY NOTE: no provider is wired up by default (VOICE_TRANSCRIPTION_PROVIDER
is None). Building and shipping an integration against a real speech-to-text
API (OpenAI Whisper API, Google Speech-to-Text, AssemblyAI, ...) would mean
either faking success without credentials to actually test it against, or
shipping unverified code -- neither is acceptable. Instead this module
defines the clean integration point (a provider interface + environment-
variable configuration) and a TranscriptionUnavailableError that surfaces
honestly to the user, exactly as requested: "show a truthful unavailable
state when credentials are absent."

The PRIMARY, fully-working transcription path for this feature is
client-side: the browser's own Web Speech API produces a real transcript
live during recording and sends that text to the backend directly (see
VoiceScanner.tsx) -- it never needs this module at all. This module only
matters for the secondary "upload a pre-recorded audio file" path.

To wire in a real provider later: implement TranscriptionProvider below,
register it in _PROVIDERS, and set VOICE_TRANSCRIPTION_PROVIDER +
VOICE_TRANSCRIPTION_API_KEY. Nothing else in the pipeline needs to change.
"""
from abc import ABC, abstractmethod

from app_service.core.config import get_settings


class TranscriptionUnavailableError(Exception):
    """Raised when server-side audio transcription was requested but no
    provider is configured. This is the honest, user-facing state -- not
    a bug to catch and hide.
    """


class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, content_type: str) -> str:
        """Returns a real transcript, or raises on failure. Implementors
        must never return a fabricated/placeholder transcript."""


# No providers are registered by default -- see module docstring. This
# dict is the extension point for a real integration.
_PROVIDERS: dict[str, type[TranscriptionProvider]] = {}


def transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    settings = get_settings()
    provider_name = settings.VOICE_TRANSCRIPTION_PROVIDER

    if not provider_name:
        raise TranscriptionUnavailableError(
            "Server-side voice transcription is not configured on this deployment. "
            "Use the in-browser microphone recorder for live transcription instead, "
            "or ask the administrator to configure VOICE_TRANSCRIPTION_PROVIDER."
        )

    provider_cls = _PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise TranscriptionUnavailableError(
            f"VOICE_TRANSCRIPTION_PROVIDER is set to '{provider_name}', which is not "
            "a recognized/implemented provider."
        )

    if not settings.VOICE_TRANSCRIPTION_API_KEY:
        raise TranscriptionUnavailableError(
            f"Voice transcription provider '{provider_name}' is selected but no "
            "VOICE_TRANSCRIPTION_API_KEY is configured."
        )

    provider = provider_cls()
    return provider.transcribe(audio_bytes, content_type)
