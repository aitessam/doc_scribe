import pytest
from fastapi.testclient import TestClient

from app.llm.processor import MedicalNote, MedicalNoteProcessor
from app.utils.exceptions import LLMResponseParseError, LLMTimeoutError
from server import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_process_returns_structured_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        MedicalNoteProcessor, "process", lambda self, t: MedicalNote(diagnosis="Migraine")
    )

    response = client.post("/process", json={"transcript": "Sar mein dard hai"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["structured_note"]["diagnosis"] == "Migraine"


def test_empty_transcript_is_rejected() -> None:
    response = client.post("/process", json={"transcript": ""})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [(LLMTimeoutError("timeout"), 504), (LLMResponseParseError("bad json"), 502)],
)
def test_domain_errors_map_to_http_status(
    monkeypatch: pytest.MonkeyPatch, error: Exception, expected_status: int
) -> None:
    def fail(self: MedicalNoteProcessor, transcript: str) -> MedicalNote:
        raise error

    monkeypatch.setattr(MedicalNoteProcessor, "process", fail)

    response = client.post("/process", json={"transcript": "Patient has fever"})

    assert response.status_code == expected_status
