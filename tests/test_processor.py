import json
from typing import Callable

import httpx
import pytest

from app.llm.processor import MedicalNoteProcessor
from app.utils.exceptions import LLMResponseParseError, LLMTimeoutError
from config.settings import Settings

NOTE = {
    "presenting_complaints": "Fever for 3 days",
    "symptoms": "Headache, body ache",
    "diagnosis": "Viral fever",
    "vitals": "Temp 101F",
    "premorbid_conditions": "Not mentioned",
    "medication": "Paracetamol 500mg",
    "lab_tests": "CBC",
    "consultation_notes": "Review in 3 days",
}

_RealClient = httpx.Client


def _settings(endpoint: str) -> Settings:
    return Settings(_env_file=None, LLM_ENDPOINT=endpoint, LLM_TIMEOUT=1)


def _mock_llm(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: _RealClient(transport=httpx.MockTransport(handler), **kw)
    )


def test_parses_clean_json() -> None:
    processor = MedicalNoteProcessor(_settings("http://localhost:11434/api/chat"))

    note = processor._parse_response(json.dumps(NOTE))

    assert note.diagnosis == "Viral fever"


def test_extracts_json_wrapped_in_prose() -> None:
    processor = MedicalNoteProcessor(_settings("http://localhost:11434/api/chat"))

    note = processor._parse_response(f"Here is the note:\n```json\n{json.dumps(NOTE)}\n```")

    assert note.medication == "Paracetamol 500mg"


def test_rejects_non_json_response() -> None:
    processor = MedicalNoteProcessor(_settings("http://localhost:11434/api/chat"))

    with pytest.raises(LLMResponseParseError):
        processor._parse_response("I could not find any clinical information.")


def test_ollama_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(200, json={"message": {"content": json.dumps(NOTE)}})

    _mock_llm(monkeypatch, handler)
    processor = MedicalNoteProcessor(_settings("http://localhost:11434/api/chat"))

    assert processor.process("Patient has fever").diagnosis == "Viral fever"


def test_openai_compatible_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["temperature"] == 0
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(NOTE)}}]})

    _mock_llm(monkeypatch, handler)
    processor = MedicalNoteProcessor(_settings("https://api.openai.com/v1/chat/completions"))

    assert processor.process("Patient has fever").lab_tests == "CBC"


def test_timeout_is_retried_then_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=request)

    _mock_llm(monkeypatch, handler)
    monkeypatch.setattr("app.llm.processor.time.sleep", lambda _: None)
    processor = MedicalNoteProcessor(_settings("http://localhost:11434/api/chat"))

    with pytest.raises(LLMTimeoutError):
        processor.process("Patient has fever")
    assert calls == 3
