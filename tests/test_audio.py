import queue
from typing import Iterator

import pytest

from app.transcription import audio


class _FakeStream:
    def __init__(self) -> None:
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _clean_audio_state() -> Iterator[None]:
    audio.audio_q = queue.Queue()
    audio._active_stream = None
    yield
    audio._active_stream = None


def test_stop_closes_stream_and_signals_end_of_stream() -> None:
    stream = _FakeStream()
    audio._active_stream = stream
    audio.audio_q.put(b"\x01\x02")

    audio.stop_stream()

    assert stream.stopped and stream.closed
    mic = audio.MicStream()
    assert mic.read(1024) == b"\x01\x02"
    assert mic.read(1024) == b""


def test_stop_is_idempotent() -> None:
    audio._active_stream = _FakeStream()

    audio.stop_stream()
    audio.stop_stream()

    assert audio.audio_q.qsize() == 1


def test_errors_inside_session_are_not_masked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio.sd, "InputStream", lambda **_: _FakeStream())

    with pytest.raises(ValueError, match="auth failed"):
        with audio.start_stream():
            raise ValueError("auth failed")

    assert audio._active_stream is None
