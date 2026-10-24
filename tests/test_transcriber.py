from typing import List

from app.transcription.transcriber import LiveTranscriber, TranscriptEvent
from config.settings import Settings


def _transcriber(partials: List[TranscriptEvent], finals: List[TranscriptEvent]) -> LiveTranscriber:
    return LiveTranscriber(
        settings=Settings(_env_file=None), on_partial=partials.append, on_final=finals.append
    )


def test_final_transcript_is_forwarded() -> None:
    partials: List[TranscriptEvent] = []
    finals: List[TranscriptEvent] = []

    _transcriber(partials, finals)._handle_final_transcript(
        {"metadata": {"transcript": "مجھے بخار ہے", "end_time": 2.5}}
    )

    assert finals == [TranscriptEvent(text="مجھے بخار ہے", is_final=True, timestamp=2.5)]
    assert partials == []


def test_empty_and_malformed_messages_are_ignored() -> None:
    partials: List[TranscriptEvent] = []
    finals: List[TranscriptEvent] = []
    transcriber = _transcriber(partials, finals)

    transcriber._handle_partial_transcript({"metadata": {"transcript": ""}})
    transcriber._handle_final_transcript({"unexpected": "payload"})

    assert partials == [] and finals == []


def test_invalid_timestamp_falls_back_to_zero() -> None:
    event = _transcriber([], [])._extract_event(
        {"metadata": {"transcript": "fever", "end_time": "n/a"}}, is_final=False
    )

    assert event.timestamp == 0.0
