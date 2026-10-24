import threading

from app.transcription.session import TranscriptSession
from app.transcription.transcriber import TranscriptEvent


def _event(text: str, is_final: bool) -> TranscriptEvent:
    return TranscriptEvent(text=text, is_final=is_final, timestamp=0.0)


def test_final_line_clears_partial() -> None:
    session = TranscriptSession()

    session.add_partial(_event("Teen din", is_final=False))
    assert session.snapshot() == ([], "Teen din")

    session.add_final(_event("Teen din se bukhar hai", is_final=True))
    assert session.snapshot() == (["Teen din se bukhar hai"], "")


def test_transcript_joins_final_lines() -> None:
    session = TranscriptSession()

    session.add_final(_event("Doctor: Kya takleef hai?", is_final=True))
    session.add_final(_event("Patient: Sar mein dard hai.", is_final=True))

    assert session.transcript == "Doctor: Kya takleef hai?\nPatient: Sar mein dard hai."


def test_snapshot_is_a_copy() -> None:
    session = TranscriptSession()
    session.add_final(_event("fever", is_final=True))

    lines, _ = session.snapshot()
    lines.append("tampered")

    assert session.snapshot()[0] == ["fever"]


def test_records_worker_error() -> None:
    session = TranscriptSession()
    assert session.error is None

    session.fail("Invalid Speechmatics API key.")

    assert session.error == "Invalid Speechmatics API key."


def test_concurrent_writes_are_not_lost() -> None:
    session = TranscriptSession()

    def write(prefix: str) -> None:
        for i in range(500):
            session.add_final(_event(f"{prefix}{i}", is_final=True))

    threads = [threading.Thread(target=write, args=(p,)) for p in "abcd"]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(session.snapshot()[0]) == 2000
