from __future__ import annotations

import threading
from typing import List, Optional, Tuple

from app.transcription.transcriber import TranscriptEvent


class TranscriptSession:
    """Thread-safe buffer shared between the transcription worker and the UI.

    The transcription thread runs without a Streamlit script context, so it must
    never touch ``st.session_state`` directly. Instead it writes into this object,
    and the UI reads consistent snapshots on each refresh.
    """

    def __init__(self) -> None:
        """Initialise an empty session."""

        self._lock = threading.Lock()
        self._lines: List[str] = []
        self._partial = ""
        self._error: Optional[str] = None

    def add_partial(self, event: TranscriptEvent) -> None:
        """Record the latest partial (in-progress) transcript text.

        Args:
            event: Partial transcript event from the transcriber.
        """

        with self._lock:
            self._partial = event.text

    def add_final(self, event: TranscriptEvent) -> None:
        """Append a finalised transcript line and clear the partial text.

        Args:
            event: Final transcript event from the transcriber.
        """

        with self._lock:
            if event.text:
                self._lines.append(event.text)
            self._partial = ""

    def fail(self, message: str) -> None:
        """Record an error raised by the transcription worker.

        Args:
            message: Human-readable error description.
        """

        with self._lock:
            self._error = message

    def snapshot(self) -> Tuple[List[str], str]:
        """Return a copy of the final lines and the current partial text.

        Returns:
            Tuple[List[str], str]: Final transcript lines and partial text.
        """

        with self._lock:
            return list(self._lines), self._partial

    @property
    def error(self) -> Optional[str]:
        """Optional[str]: Error message from the worker, if any."""

        with self._lock:
            return self._error

    @property
    def transcript(self) -> str:
        """str: Full transcript built from the finalised lines."""

        with self._lock:
            return "\n".join(self._lines).strip()
