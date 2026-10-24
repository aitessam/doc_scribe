from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Audio capture configuration.

    Args:
        sample_rate: Audio sample rate in Hertz.
        channels: Number of channels (1 for mono, 2 for stereo).
        dtype: Sample data type for the audio interface (for example, "int16").
    """

    sample_rate: int
    channels: int
    dtype: str = "int16"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file.

    This settings class centralizes all configuration for the DocScribe application.
    Values are loaded from process environment variables and an optional `.env` file
    at the project root. Field names are aligned with the corresponding environment
    variable names defined in the PRD.

    Attributes:
        SPEECHMATICS_API_KEY: API key for authenticating with the Speechmatics
            real-time transcription service. This value is required and has no
            default; the application will fail to start if it is missing.
        SPEECHMATICS_URL: WebSocket endpoint URL for the Speechmatics real-time
            API.
        SPEECHMATICS_LANGUAGE: Language code used by Speechmatics for
            transcription (for example, "ur" for Urdu).
        AUDIO_SAMPLE_RATE: Audio capture sample rate in Hertz (for example,
            16000 for 16kHz).
        AUDIO_CHANNELS: Number of audio channels to capture (1 for mono, 2 for
            stereo).
        LLM_ENDPOINT: URL of the LLM backend endpoint that receives transcript
            text and returns structured medical notes.
        LLM_MODEL: Identifier of the LLM model to use at the configured
            endpoint.
        LLM_TIMEOUT: Timeout in seconds for LLM requests.
        API_HOST: Hostname or IP address FastAPI should bind to.
        API_PORT: TCP port FastAPI should listen on.
        TRANSCRIPT_OUTPUT_DIR: Directory where raw transcript files are stored.
        NOTES_OUTPUT_DIR: Directory where structured medical note files are
            stored.
        ENABLE_FILE_SAVING: Flag indicating whether transcripts and notes should
            be persisted to disk.
        LOG_LEVEL: Logging verbosity level (for example, "DEBUG", "INFO",
            "WARNING").
        LOG_FILE: Path to the log file used by the application's logging
            configuration.
    """

    # Speechmatics Configuration
    SPEECHMATICS_API_KEY: str = Field(
        ...,
        description="API key for the Speechmatics real-time transcription service.",
    )
    SPEECHMATICS_URL: str = Field(
        "wss://eu2.rt.speechmatics.com/v2",
        description="WebSocket URL for the Speechmatics real-time API.",
    )
    SPEECHMATICS_LANGUAGE: str = Field(
        "ur",
        description="Language code for Speechmatics transcription (e.g., 'ur').",
    )

    # Audio Configuration
    AUDIO_SAMPLE_RATE: int = Field(
        16000,
        description="Audio sample rate in Hz.",
    )
    AUDIO_CHANNELS: int = Field(
        1,
        description="Number of audio channels to capture.",
    )

    # LLM Backend Configuration
    LLM_ENDPOINT: str = Field(
        "http://localhost:11434/api/chat",
        description="HTTP endpoint for the LLM backend.",
    )
    LLM_MODEL: str = Field(
        "mistral",
        description="Model identifier for the LLM backend.",
    )
    LLM_TIMEOUT: int = Field(
        120,
        description="Timeout in seconds for LLM requests.",
    )

    # Server Configuration
    API_HOST: str = Field(
        "127.0.0.1",
        description="Host interface for the FastAPI server.",
    )
    API_PORT: int = Field(
        8000,
        description="Port for the FastAPI server.",
    )

    # File Output
    TRANSCRIPT_OUTPUT_DIR: Path = Field(
        Path("./outputs/transcripts"),
        description="Directory for saving transcript files.",
    )
    NOTES_OUTPUT_DIR: Path = Field(
        Path("./outputs/notes"),
        description="Directory for saving structured note files.",
    )
    ENABLE_FILE_SAVING: bool = Field(
        True,
        description="Whether to persist transcripts and notes to disk.",
    )

    # Logging
    LOG_LEVEL: str = Field(
        "INFO",
        description="Logging level for the application.",
    )
    LOG_FILE: Path = Field(
        Path("./logs/docscribe.log"),
        description="Path to the application log file.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings.

    This function uses an LRU cache with a maximum size of one to ensure that
    the `Settings` instance is created only once per process. Subsequent calls
    return the same instance, providing a lightweight singleton pattern for
    configuration access across the application.

    Returns:
        Settings: The singleton settings instance loaded from the environment.
    """

    return Settings()
