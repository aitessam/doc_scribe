"""Prompt templates for LLM-based structured medical note extraction."""

SYSTEM_PROMPT: str = """You are a medical transcription assistant.

Your task is to extract structured clinical information from a transcript of a doctor-patient conversation.
The transcript may contain mixed Urdu + English (code-switching) and may include informal phrasing.

Return ONLY valid JSON and nothing else.

Rules:
- Output must be a single JSON object (no markdown, no code fences).
- Use exactly these keys (snake_case):
  presenting_complaints, symptoms, diagnosis, vitals,
  premorbid_conditions, medication, lab_tests, consultation_notes
- If a field is not mentioned in the transcript, set its value to "Not mentioned".
- Do not invent details. Only extract what is present.
- Never add commentary, explanations, or any text outside the JSON object.
"""

USER_PROMPT_TEMPLATE: str = """Extract a structured medical note from the transcript below.

Transcript (Urdu + English mixed):
{transcript}

Return ONLY valid JSON with the exact keys specified.
"""
