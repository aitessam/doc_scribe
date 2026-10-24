import json
from contextlib import contextmanager
from typing import Any, Callable, Iterator

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.transcription import audio, transcriber
from app.transcription.transcriber import TranscriptEvent

_RealClient = httpx.Client


class _FakeTranscriber:
    """Emits a scripted conversation instead of streaming to Speechmatics."""

    def __init__(
        self,
        settings: Any,
        on_partial: Callable[[TranscriptEvent], None],
        on_final: Callable[[TranscriptEvent], None],
    ) -> None:
        self._on_partial = on_partial
        self._on_final = on_final

    def start(self, mic_stream: Any) -> None:
        self._on_partial(TranscriptEvent("Patient has", is_final=False, timestamp=0.5))
        self._on_final(TranscriptEvent("Patient has fever", is_final=True, timestamp=1.0))


@contextmanager
def _fake_stream() -> Iterator[None]:
    yield None


def _click(app: AppTest, label: str) -> AppTest:
    next(b for b in app.button if b.label == label).click()
    return app.run()


def test_app_renders_idle_state() -> None:
    app = AppTest.from_file("streamlit_app.py").run()

    assert not app.exception
    assert app.subheader[0].value == "Live Transcript"
    labels = [button.label for button in app.button]
    assert "Start Recording" in labels and "Stop & Generate Note" in labels


def test_record_then_generate_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio, "start_stream", _fake_stream)
    monkeypatch.setattr(audio, "stop_stream", lambda: None)
    monkeypatch.setattr(transcriber, "LiveTranscriber", _FakeTranscriber)

    def api(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {"transcript": "Patient has fever"}
        return httpx.Response(200, json={"structured_note": {"diagnosis": "Viral fever"}})

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: _RealClient(transport=httpx.MockTransport(api), **kw)
    )

    app = AppTest.from_file("streamlit_app.py").run()
    app = _click(app, "Start Recording")
    app.session_state["transcription_thread"].join(timeout=5)
    app = app.run()

    assert any("Patient has fever" in md.value for md in app.markdown)

    app = _click(app, "Stop & Generate Note")

    assert not app.exception
    assert app.session_state["status"] == "NOTE_READY"
    assert any("Viral fever" in md.value for md in app.markdown)
