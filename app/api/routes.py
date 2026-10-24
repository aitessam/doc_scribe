from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, constr

from app.llm.processor import MedicalNoteProcessor
from app.utils.exceptions import (
    AudioCaptureError,
    DocScribeError,
    FileExportError,
    LLMResponseParseError,
    LLMTimeoutError,
    TranscriptionAuthError,
    TranscriptionConnectionError,
)
from app.utils.logger import get_logger
from config.settings import get_settings

router = APIRouter()
_logger = get_logger(__name__)

_APP_VERSION = "1.0.0"


class TranscriptRequest(BaseModel):
    """Request body for transcript processing."""

    transcript: constr(min_length=1, max_length=50000) = Field(
        ...,
        description="Non-empty transcript text (max 50,000 characters).",
    )


class NoteResponse(BaseModel):
    """Response body for structured note generation."""

    structured_note: dict[str, Any]
    success: bool
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response body."""

    status: str
    version: str


def _raise_for_docscribe_error(exc: DocScribeError) -> None:
    """Map DocScribeError subclasses to HTTP status codes and raise HTTPException.

    Args:
        exc: A DocScribe domain exception.

    Raises:
        HTTPException: Always raised with the appropriate status code and message.
    """

    if isinstance(exc, TranscriptionAuthError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    if isinstance(exc, TranscriptionConnectionError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        )
    if isinstance(exc, LLMTimeoutError):
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message)
    if isinstance(exc, LLMResponseParseError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message)
    if isinstance(exc, (AudioCaptureError, FileExportError)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message)

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message)


@router.post("/process", response_model=NoteResponse)
def process_transcript(payload: TranscriptRequest) -> NoteResponse:
    """Process a transcript and return a structured medical note as JSON.

    Args:
        payload: Request payload containing the transcript text.

    Returns:
        NoteResponse: Response containing the structured note and status flags.

    Raises:
        HTTPException: For validation errors or any DocScribe processing errors.
    """

    settings = get_settings()
    processor = MedicalNoteProcessor(settings)

    try:
        note = processor.process(payload.transcript)
        return NoteResponse(structured_note=note.model_dump(), success=True, error=None)
    except DocScribeError as exc:
        _logger.exception("DocScribeError while processing transcript: %s", exc)
        _raise_for_docscribe_error(exc)
    except Exception as exc:
        _logger.exception("Unexpected error while processing transcript: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error.",
        ) from exc


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a health check response.

    Returns:
        HealthResponse: Health status and application version.
    """

    return HealthResponse(status="ok", version=_APP_VERSION)
