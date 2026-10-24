from __future__ import annotations

import threading
from typing import Dict, Literal, Optional

import httpx
import streamlit as st

from app.transcription.audio import start_stream, stop_stream
from app.transcription.session import TranscriptSession
from app.transcription.transcriber import LiveTranscriber
from app.utils.logger import get_logger
from app.utils.urdu_text import render_urdu
from config.settings import get_settings

StatusState = Literal["IDLE", "RECORDING", "PROCESSING", "NOTE_READY", "ERROR"]

# How often the live transcript panel refreshes while recording, in seconds.
_LIVE_REFRESH_SECONDS = 1.0
# How long to wait for Speechmatics to flush final transcripts after stopping.
_STOP_TIMEOUT_SECONDS = 10.0

_logger = get_logger(__name__)


def _init_session_state() -> None:
    """Initialize Streamlit session state keys if they are missing."""

    defaults = {
        "recording": False,
        "session": TranscriptSession(),
        "structured_note": None,
        "status": "IDLE",
        "error_message": None,
        "transcription_thread": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_transcription_thread(session: TranscriptSession) -> None:
    """Background worker that manages audio capture and live transcription.

    This runs outside the Streamlit script context, so it only writes to the
    thread-safe `session` and never touches ``st.session_state``.

    Args:
        session: Shared buffer that receives transcript events and errors.
    """

    transcriber = LiveTranscriber(
        settings=get_settings(), on_partial=session.add_partial, on_final=session.add_final
    )

    try:
        with start_stream() as mic_stream:
            transcriber.start(mic_stream)
    except Exception as exc:
        _logger.exception("Error during live transcription: %s", exc)
        session.fail(str(exc))


def start_recording() -> None:
    """Start recording audio and live transcription."""

    if st.session_state.recording:
        return

    session = TranscriptSession()
    st.session_state.session = session
    st.session_state.recording = True
    st.session_state.status = "RECORDING"
    st.session_state.structured_note = None
    st.session_state.error_message = None

    thread = threading.Thread(target=_run_transcription_thread, args=(session,), daemon=True)
    st.session_state.transcription_thread = thread
    thread.start()


def stop_and_generate() -> None:
    """Stop recording and request structured note generation from the API."""

    if not st.session_state.recording:
        return

    st.session_state.status = "PROCESSING"
    st.session_state.recording = False

    try:
        # Closing the stream signals end of audio so Speechmatics can flush.
        stop_stream()
    except Exception as exc:  # pragma: no cover - defensive
        _logger.warning("Error while stopping audio stream: %s", exc)

    thread: Optional[threading.Thread] = st.session_state.get("transcription_thread")
    if thread is not None and thread.is_alive():
        thread.join(timeout=_STOP_TIMEOUT_SECONDS)

    session: TranscriptSession = st.session_state.session
    transcript_text = session.transcript
    if not transcript_text:
        st.session_state.status = "ERROR"
        st.session_state.error_message = session.error or "No transcript recorded."
        return

    settings = get_settings()
    api_url = f"http://{settings.API_HOST}:{settings.API_PORT}/process"

    try:
        with httpx.Client(timeout=settings.LLM_TIMEOUT) as client:
            response = client.post(api_url, json={"transcript": transcript_text})
            response.raise_for_status()
            data: Dict[str, object] = response.json()

        structured_note = data.get("structured_note")
        if not isinstance(structured_note, dict):
            raise ValueError("API response missing 'structured_note' object.")

        st.session_state.structured_note = structured_note
        st.session_state.status = "NOTE_READY"
    except Exception as exc:
        _logger.exception("Error while generating structured note: %s", exc)
        st.session_state.status = "ERROR"
        st.session_state.error_message = str(exc)


def _render_status_badge(status: StatusState) -> None:
    """Render a small status badge in the top bar."""

    color = {
        "IDLE": "gray",
        "RECORDING": "green",
        "PROCESSING": "orange",
        "NOTE_READY": "blue",
        "ERROR": "red",
    }.get(status, "gray")
    label = {
        "IDLE": "READY",
        "RECORDING": "LIVE",
        "PROCESSING": "PROCESSING",
        "NOTE_READY": "NOTE READY",
        "ERROR": "ERROR",
    }.get(status, status)

    st.markdown(
        f"<span style='padding:4px 8px;border-radius:12px;background-color:{color};"
        f"color:white;font-size:0.8rem;'>{label}</span>",
        unsafe_allow_html=True,
    )


def _render_top_bar() -> None:
    """Render the top control bar with title, status, and buttons."""

    left, middle, right = st.columns([4, 2, 3])
    with left:
        st.markdown("### DocScribe 🎙️")
    with middle:
        _render_status_badge(st.session_state.status)
    with right:
        cols = st.columns(2)
        with cols[0]:
            start_disabled = st.session_state.recording or st.session_state.status == "PROCESSING"
            st.button("Start Recording", on_click=start_recording, disabled=start_disabled)
        with cols[1]:
            stop_disabled = not st.session_state.recording
            st.button("Stop & Generate Note", on_click=stop_and_generate, disabled=stop_disabled)


def _render_live_transcript() -> None:
    """Render transcript lines from the shared session.

    Runs as a fragment that refreshes on a timer while recording, so live
    updates from the worker thread appear without a full page rerun.
    """

    session: TranscriptSession = st.session_state.session

    if st.session_state.recording and session.error:
        st.session_state.recording = False
        st.session_state.status = "ERROR"
        st.session_state.error_message = session.error
        st.rerun()

    lines, partial = session.snapshot()
    for line in lines:
        st.markdown(render_urdu(line))

    if partial:
        st.markdown(f"<i>{render_urdu(partial)}</i>", unsafe_allow_html=True)


def _render_transcript_panel() -> None:
    """Render the live transcript panel."""

    st.subheader("Live Transcript")
    run_every = _LIVE_REFRESH_SECONDS if st.session_state.recording else None
    st.fragment(_render_live_transcript, run_every=run_every)()

    transcript = st.session_state.session.transcript
    st.download_button(
        label="Download Transcript (.txt)",
        data=transcript,
        file_name="transcript.txt",
        mime="text/plain",
        disabled=st.session_state.recording or not transcript,
    )


def _render_structured_note_panel() -> None:
    """Render the structured medical note panel."""

    st.subheader("Structured Medical Note")
    note: Optional[Dict[str, str]] = st.session_state.structured_note

    if not note:
        st.info("No structured note generated yet. Stop recording to generate a note.")
        return

    field_labels = {
        "presenting_complaints": "Presenting Complaints",
        "symptoms": "Symptoms",
        "diagnosis": "Diagnosis",
        "vitals": "Vitals",
        "premorbid_conditions": "Premorbid Conditions",
        "medication": "Medication",
        "lab_tests": "Laboratory Tests",
        "consultation_notes": "Consultation Notes",
    }

    for key, label in field_labels.items():
        value = note.get(key, "")
        with st.expander(label, expanded=True):
            st.markdown(value or "Not mentioned")

    note_text = "\n\n".join(
        f"{label}:\n{note.get(key, '') or 'Not mentioned'}" for key, label in field_labels.items()
    )

    st.download_button(
        label="Download Structured Note (.txt)",
        data=note_text,
        file_name="structured_note.txt",
        mime="text/plain",
        disabled=not st.session_state.structured_note,
    )


def main() -> None:
    """Entry point for the Streamlit application."""

    st.set_page_config(page_title="DocScribe", layout="wide")
    _init_session_state()

    _render_top_bar()

    if st.session_state.status == "ERROR" and st.session_state.error_message:
        st.error(st.session_state.error_message)

    left_col, right_col = st.columns([6, 4])
    with left_col:
        _render_transcript_panel()
    with right_col:
        _render_structured_note_panel()


if __name__ == "__main__":
    main()
