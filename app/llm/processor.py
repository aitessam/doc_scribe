from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from app.llm.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.utils.exceptions import LLMResponseParseError, LLMTimeoutError
from app.utils.logger import get_logger
from config.settings import Settings


class MedicalNote(BaseModel):
    """Structured medical note extracted from a transcript.

    All fields are optional strings. When a field is not present in the transcript,
    the LLM is instructed to return "Not mentioned", but this model allows `None`
    to support partial or fallback parsing.
    """

    presenting_complaints: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    vitals: Optional[str] = None
    premorbid_conditions: Optional[str] = None
    medication: Optional[str] = None
    lab_tests: Optional[str] = None
    consultation_notes: Optional[str] = None


class MedicalNoteProcessor:
    """LLM-backed processor that converts transcripts into structured medical notes."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the processor.

        Args:
            settings: Application settings containing LLM endpoint, model, and timeout.
        """

        self._settings = settings
        self._logger = get_logger(__name__)

    def process(self, transcript: str) -> MedicalNote:
        """Process a transcript into a structured medical note.

        Args:
            transcript: Raw transcript text (may include Urdu + English mixed content).

        Returns:
            MedicalNote: Parsed structured medical note.

        Raises:
            LLMTimeoutError: If the LLM call times out after retrying.
            LLMResponseParseError: If the LLM response cannot be parsed into JSON.
        """

        prompt = USER_PROMPT_TEMPLATE.format(transcript=transcript)
        raw = self._call_llm(prompt)
        return self._parse_response(raw)

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM backend and return the raw text response.

        Supports both Ollama Chat API format and OpenAI-compatible Chat Completions
        format. Endpoint selection is based on whether `LLM_ENDPOINT` contains
        "ollama" or "openai" (case-insensitive).

        Retry logic:
        - Retries timeouts 2 times with a 5 second delay between attempts.

        Args:
            prompt: The user prompt to send to the model.

        Returns:
            str: Raw model output text (expected to be JSON string).

        Raises:
            LLMTimeoutError: If the call times out after retries.
            LLMResponseParseError: If the backend responds with an unexpected payload.
        """

        endpoint = self._settings.LLM_ENDPOINT
        endpoint_lc = endpoint.lower()
        backend: str
        if "ollama" in endpoint_lc:
            backend = "ollama"
        elif "openai" in endpoint_lc:
            backend = "openai"
        else:
            # Heuristic fallback to avoid brittle configuration: common Ollama path.
            backend = "ollama" if "/api/chat" in endpoint_lc else "openai"

        timeout_seconds = float(self._settings.LLM_TIMEOUT)
        attempts = 3  # initial + 2 retries

        last_timeout_exc: Optional[BaseException] = None

        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(timeout=httpx.Timeout(timeout_seconds)) as client:
                    if backend == "ollama":
                        payload: Dict[str, Any] = {
                            "model": self._settings.LLM_MODEL,
                            "stream": False,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": prompt},
                            ],
                        }
                        res = client.post(endpoint, json=payload)
                        res.raise_for_status()
                        data = res.json()

                        message = data.get("message")
                        if isinstance(message, dict) and isinstance(message.get("content"), str):
                            return message["content"]
                        if isinstance(data.get("response"), str):
                            # Some Ollama endpoints return `response` instead of chat `message`.
                            return data["response"]
                        raise LLMResponseParseError(
                            "Unexpected Ollama response payload structure."
                        )

                    payload = {
                        "model": self._settings.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0,
                    }
                    res = client.post(endpoint, json=payload)
                    res.raise_for_status()
                    data = res.json()

                    choices = data.get("choices")
                    if isinstance(choices, list) and choices:
                        choice0 = choices[0]
                        if isinstance(choice0, dict):
                            msg = choice0.get("message")
                            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                                return msg["content"]
                            text = choice0.get("text")
                            if isinstance(text, str):
                                return text

                    raise LLMResponseParseError(
                        "Unexpected OpenAI-compatible response payload structure."
                    )

            except httpx.TimeoutException as exc:
                last_timeout_exc = exc
                if attempt < attempts:
                    self._logger.warning(
                        "LLM request timed out (attempt %d/%d). Retrying in 5s.",
                        attempt,
                        attempts,
                    )
                    time.sleep(5)
                    continue
                raise LLMTimeoutError(
                    "LLM request timed out after retries.", cause=exc
                ) from exc
            except LLMResponseParseError:
                raise
            except Exception as exc:
                raise LLMResponseParseError(
                    "Failed to call LLM endpoint.", cause=exc
                ) from exc

        raise LLMTimeoutError("LLM request timed out.", cause=last_timeout_exc)

    def _parse_response(self, raw: str) -> MedicalNote:
        """Parse a raw LLM response into a `MedicalNote`.

        The LLM is instructed to return only JSON. This method is defensive and
        attempts to extract the first JSON object from the response if extra text
        appears.

        Args:
            raw: Raw string returned by the LLM backend.

        Returns:
            MedicalNote: Parsed medical note.

        Raises:
            LLMResponseParseError: If the response cannot be parsed as valid JSON
                matching the expected schema.
        """

        try:
            raw_str = raw.strip()
            start = raw_str.find("{")
            end = raw_str.rfind("}")
            if start == -1 or end == -1 or end < start:
                raise ValueError("No JSON object found in LLM response.")

            json_str = raw_str[start : end + 1]
            data = json.loads(json_str)
            if not isinstance(data, dict):
                raise TypeError("LLM response JSON root is not an object.")

            return MedicalNote.model_validate(data)
        except Exception as exc:
            raise LLMResponseParseError(
                "Failed to parse LLM response into MedicalNote.", cause=exc
            ) from exc
