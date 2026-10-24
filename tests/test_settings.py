import pytest
from pydantic import ValidationError

from config.settings import Settings


def test_defaults_are_applied() -> None:
    settings = Settings(_env_file=None)

    assert settings.SPEECHMATICS_LANGUAGE == "ur"
    assert settings.AUDIO_SAMPLE_RATE == 16000
    assert settings.API_PORT == 8000


def test_environment_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "llama3")
    monkeypatch.setenv("API_PORT", "9000")

    settings = Settings(_env_file=None)

    assert settings.LLM_MODEL == "llama3"
    assert settings.API_PORT == 9000


def test_missing_api_key_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEECHMATICS_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
