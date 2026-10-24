from __future__ import annotations

from typing import Optional


class DocScribeError(Exception):
    """Base exception for all DocScribe errors.

    This exception provides a consistent interface for attaching a human-readable
    message and an optional underlying cause (original exception).

    Args:
        message: Human-readable description of the error.
        cause: Optional underlying exception that triggered this error.

    Attributes:
        message: Human-readable description of the error.
        cause: Optional underlying exception that triggered this error.
    """

    def __init__(self, message: str, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class AudioCaptureError(DocScribeError):
    """Raised when microphone/audio capture fails."""


class TranscriptionConnectionError(DocScribeError):
    """Raised when the transcription service connection fails or drops."""


class TranscriptionAuthError(DocScribeError):
    """Raised when transcription authentication fails (e.g., invalid API key)."""


class LLMTimeoutError(DocScribeError):
    """Raised when an LLM request exceeds the configured timeout."""


class LLMResponseParseError(DocScribeError):
    """Raised when an LLM response cannot be parsed into the expected format."""


class FileExportError(DocScribeError):
    """Raised when saving or exporting transcripts/notes fails."""
