import pytest

from app_service.services.voice_transcription import transcribe_audio, TranscriptionUnavailableError
from app_service.core.config import get_settings


class TestNoProviderConfigured:
    def test_raises_unavailable_when_no_provider_set(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.delenv("VOICE_TRANSCRIPTION_PROVIDER", raising=False)
        with pytest.raises(TranscriptionUnavailableError, match="not configured"):
            transcribe_audio(b"fake audio bytes", "audio/wav")
        get_settings.cache_clear()

    def test_error_message_never_implies_a_transcript_was_produced(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.delenv("VOICE_TRANSCRIPTION_PROVIDER", raising=False)
        try:
            transcribe_audio(b"fake audio bytes", "audio/wav")
            assert False, "should have raised"
        except TranscriptionUnavailableError as exc:
            message = str(exc).lower()
            assert "transcript" not in message.split("configured")[0] or "not configured" in message
        get_settings.cache_clear()


class TestUnknownProviderConfigured:
    def test_raises_unavailable_for_unrecognized_provider_name(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.setenv("VOICE_TRANSCRIPTION_PROVIDER", "some-provider-that-does-not-exist")
        with pytest.raises(TranscriptionUnavailableError, match="not a recognized"):
            transcribe_audio(b"fake audio bytes", "audio/wav")
        monkeypatch.delenv("VOICE_TRANSCRIPTION_PROVIDER", raising=False)
        get_settings.cache_clear()


class TestNeverFabricatesATranscript:
    def test_function_never_returns_a_string_when_unconfigured(self, monkeypatch):
        # Belt-and-suspenders: confirm the function path that would
        # "succeed" is genuinely unreachable with no provider configured
        # -- it must always raise, never return a placeholder string.
        get_settings.cache_clear()
        monkeypatch.delenv("VOICE_TRANSCRIPTION_PROVIDER", raising=False)
        with pytest.raises(TranscriptionUnavailableError):
            result = transcribe_audio(b"", "audio/wav")
            assert False, f"should have raised, got {result!r} instead"
        get_settings.cache_clear()
