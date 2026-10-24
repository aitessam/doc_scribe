from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import speechmatics
from httpx import HTTPStatusError

from app.transcription.audio import MicStream
from app.utils.exceptions import TranscriptionAuthError, TranscriptionConnectionError
from app.utils.logger import get_logger
from config.settings import Settings


@dataclass(frozen=True)
class TranscriptEvent:
    """Represents a partial or final transcript event from Speechmatics.

    Attributes:
        text: The transcript text content.
        is_final: ``True`` if this is a finalized transcript segment, otherwise
            ``False`` for partial/live updates.
        timestamp: The event timestamp in seconds, based on metadata provided by
            Speechmatics (falls back to ``0.0`` when not available).
    """

    text: str
    is_final: bool
    timestamp: float


class LiveTranscriber:
    """Wrapper around the Speechmatics WebsocketClient for live transcription.

    This class manages the Speechmatics WebSocket connection, registers event
    handlers for partial and final transcripts, and provides a simple interface
    for starting and stopping live transcription sessions.
    """

    def __init__(
        self,
        settings: Settings,
        on_partial: Callable[[TranscriptEvent], None],
        on_final: Callable[[TranscriptEvent], None],
    ) -> None:
        """Initialize the live transcriber.

        Args:
            settings: Global application settings, used for Speechmatics URL,
                API key, language, and audio configuration.
            on_partial: Callback invoked for each partial transcript event.
            on_final: Callback invoked for each final transcript event.
        """

        self._settings = settings
        self._on_partial = on_partial
        self._on_final = on_final
        self._logger = get_logger(__name__)
        self._client: Optional[speechmatics.client.WebsocketClient] = None

    def _build_transcription_config(
        self,
    ) -> speechmatics.models.TranscriptionConfig:
        """Build the Speechmatics transcription configuration.

        Returns:
            speechmatics.models.TranscriptionConfig: Configured transcription
            settings, including language, operating point, and partials.
        """

        return speechmatics.models.TranscriptionConfig(
            operating_point="enhanced",
            language=self._settings.SPEECHMATICS_LANGUAGE,
            enable_partials=True,
            max_delay=4,
            max_delay_mode="flexible",
        )

    def _build_audio_settings(self) -> speechmatics.models.AudioSettings:
        """Build the Speechmatics audio settings configuration.

        Returns:
            speechmatics.models.AudioSettings: Configured audio settings for
            the streaming client.
        """

        return speechmatics.models.AudioSettings(
            encoding="pcm_s16le",
            sample_rate=self._settings.AUDIO_SAMPLE_RATE,
        )

    def _create_client(self) -> speechmatics.client.WebsocketClient:
        """Create and configure a Speechmatics WebsocketClient instance."""

        connection_settings = speechmatics.models.ConnectionSettings(
            url=self._settings.SPEECHMATICS_URL,
            auth_token=self._settings.SPEECHMATICS_API_KEY,
        )
        client = speechmatics.client.WebsocketClient(connection_settings)

        client.add_event_handler(
            event_name=speechmatics.models.ServerMessageType.AddPartialTranscript,
            event_handler=self._handle_partial_transcript,
        )
        client.add_event_handler(
            event_name=speechmatics.models.ServerMessageType.AddTranscript,
            event_handler=self._handle_final_transcript,
        )

        return client

    def _extract_event(self, msg: Dict[str, object], is_final: bool) -> TranscriptEvent:
        """Convert a Speechmatics message into a TranscriptEvent.

        Args:
            msg: Raw message dictionary from Speechmatics.
            is_final: Whether this message represents a final transcript.

        Returns:
            TranscriptEvent: Normalized transcript event.
        """

        metadata = msg.get("metadata", {}) if isinstance(msg, dict) else {}
        text = ""
        timestamp = 0.0

        if isinstance(metadata, dict):
            text = str(metadata.get("transcript", "") or "")
            # Speechmatics messages often include end_time in seconds.
            raw_time = metadata.get("end_time", 0.0)
            try:
                timestamp = float(raw_time) if raw_time is not None else 0.0
            except (TypeError, ValueError):
                timestamp = 0.0

        return TranscriptEvent(text=text, is_final=is_final, timestamp=timestamp)

    def _handle_partial_transcript(self, msg: Dict[str, object]) -> None:
        """Internal handler for partial transcript events."""

        event = self._extract_event(msg, is_final=False)
        if event.text:
            self._logger.debug("Received partial transcript: %s", event.text)
            self._on_partial(event)

    def _handle_final_transcript(self, msg: Dict[str, object]) -> None:
        """Internal handler for final transcript events."""

        event = self._extract_event(msg, is_final=True)
        if event.text:
            self._logger.info("Received final transcript: %s", event.text)
            self._on_final(event)

    def start(self, mic_stream: MicStream) -> None:
        """Start the live transcription session using the provided MicStream.

        This method establishes the WebSocket connection to Speechmatics,
        registers event handlers, and begins streaming audio from the given
        microphone stream. Connection failures are retried with exponential
        backoff up to three attempts.

        Args:
            mic_stream: Microphone stream providing PCM audio via ``read()``.

        Raises:
            TranscriptionAuthError: If authentication with Speechmatics fails
                (HTTP 401).
            TranscriptionConnectionError: If the connection fails after the
                maximum number of retries.
        """

        self._client = self._create_client()
        transcription_config = self._build_transcription_config()
        audio_settings = self._build_audio_settings()

        max_attempts = 3
        backoff_seconds = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                self._logger.info(
                    "Starting Speechmatics transcription (attempt %d/%d).",
                    attempt,
                    max_attempts,
                )
                self._client.run_synchronously(
                    mic_stream, transcription_config, audio_settings
                )
                self._logger.info("Speechmatics transcription session ended normally.")
                return
            except HTTPStatusError as exc:
                if exc.response is not None and exc.response.status_code == 401:
                    self._logger.error("Speechmatics authentication failed (401).")
                    raise TranscriptionAuthError(
                        "Invalid Speechmatics API key.", cause=exc
                    ) from exc

                self._logger.error(
                    "Speechmatics HTTP error during transcription: %s", exc
                )
                raise TranscriptionConnectionError(
                    "Speechmatics HTTP error during transcription.", cause=exc
                ) from exc
            except Exception as exc:
                self._logger.warning(
                    "Speechmatics connection error on attempt %d/%d: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt >= max_attempts:
                    raise TranscriptionConnectionError(
                        "Failed to maintain Speechmatics connection after retries.",
                        cause=exc,
                    ) from exc

                time.sleep(backoff_seconds)
                backoff_seconds *= 2

    def stop(self) -> None:
        """Stop the live transcription session and close the WebSocket client."""

        if self._client is None:
            return

        try:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()
            self._logger.info("Speechmatics transcription client stopped.")
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("Error while stopping Speechmatics client: %s", exc)
        finally:
            self._client = None

