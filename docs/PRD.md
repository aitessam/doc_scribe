**DocScribe**

Real-Time Medical Transcription & Note Generation

_Product Requirements Document (PRD)_

| **Version** | 1.0.0 |
| --- | --- |
| **Status** | Draft - For Development |
| **Date** | 2025 |
| **Target Stack** | Python \| Streamlit \| Speechmatics \| Ollama/LLM |
| **License** | MIT |

_This PRD describes the full product design and architecture for DocScribe, an open-source system for real-time Urdu+English medical transcription and structured note generation._

# **1\. Product Overview**

DocScribe is an open-source, AI-powered system that performs real-time transcription of doctor-patient conversations (Urdu and English) and automatically converts them into structured medical notes using a large language model. The system is designed to reduce the documentation burden on physicians while improving the completeness and consistency of clinical records.

The system is built for deployment in outpatient clinics, telemedicine platforms, and hospital consultation rooms where doctors interact with patients in bilingual (Urdu/English) settings common in Pakistan, India, and similar South Asian healthcare environments.

## **Target Users**

| **User Type** | **Use Case** |
| --- | --- |
| **General Practitioners** | Primary users in outpatient settings needing fast, accurate documentation |
| **Specialist Physicians** | Cardiologists, neurologists, etc. requiring detailed structured notes |
| **Telemedicine Platforms** | Remote consultation services needing automated note generation |
| **Medical Transcriptionists** | Professionals who want AI-assisted review and structuring |
| **Healthcare IT Teams** | Teams integrating AI documentation into clinical workflows or EHR systems |

_The project evolves an earlier single-script prototype (Speechmatics WebSocket transcription plus a remote Ollama endpoint for structuring) into a clean, modular, production-ready open-source product._

# **2\. Problem Statement**

Manual medical documentation is one of the most time-consuming and error-prone aspects of clinical practice. Physicians in high-volume outpatient settings often spend 30-40% of their working hours on documentation rather than patient care. This problem is significantly compounded in multilingual contexts:

- Urdu-speaking patients often explain symptoms and history in Urdu, while doctors record notes in English
- This language switch requires real-time mental translation, increasing cognitive load and documentation errors
- Missed or incomplete notes can lead to incorrect follow-up diagnoses and medication errors
- Manual note-taking during consultations reduces eye contact and patient trust
- Small clinics and rural settings lack resources for dedicated medical transcriptionists

## **Key Pain Points**

| **Pain Point** | **Description** |
| --- | --- |
| **Time Burden** | Physicians spend excessive time on post-consultation documentation |
| **Multilingual Gap** | No existing tools handle Urdu-English code-switching in medical contexts |
| **Incomplete Records** | Rushed notes miss critical clinical details like medication history or vitals |
| **No Affordable Tools** | Existing medical transcription software is expensive and English-only |
| **Lack of Structure** | Free-text notes are inconsistent and hard to query for analytics |

# **3\. Goals and Objectives**

## **Primary Goals**

- Enable real-time bilingual (Urdu + English) transcription of doctor-patient conversations
- Convert raw transcripts automatically into standardized structured medical notes
- Provide a clean, intuitive Streamlit-based UI that any physician can use without technical training
- Package as a fully open-source, MIT-licensed GitHub project with Docker support
- Support flexible LLM backends: local Ollama models and OpenAI-compatible API endpoints

## **Success Metrics**

| **Metric** | **Target** |
| --- | --- |
| **Transcription Latency** | < 4 seconds end-to-end for real-time partial transcription |
| **Note Generation Time** | < 30 seconds for LLM structuring of a 10-minute consultation |
| **Structured Output Quality** | All 8 required fields populated from a complete consultation |
| **UI Simplicity** | Doctor can start recording within 2 clicks of opening the app |
| **Open Source Adoption** | Clear README enabling setup in < 15 minutes on a local machine |

# **4\. Key Features**

## **Core Features**

- **Real-Time Audio Capture - Microphone input via sounddevice with configurable sample rate (16kHz, mono)**
  - Works with system default mic or selectable audio input devices
  - Configurable audio buffer for low-latency streaming
- **Live Speechmatics Transcription - WebSocket connection to Speechmatics real-time API**
  - Supports Urdu language code (ur) with enhanced operating point
  - Partial transcripts displayed with < 1 second lag for real-time feedback
  - Final transcripts appended to session log with timestamps
- **Bilingual Urdu + English Support - Handles code-switching between languages mid-sentence**
  - Uses arabic-reshaper and python-bidi for correct Urdu RTL rendering
  - Transcript saved in UTF-8 encoding for Urdu character preservation
- **LLM-Powered Structured Note Generation - Transcript sent to LLM backend on session end**
  - Supports Ollama local models (Mistral, LLaMA 3, Qwen, etc.)
  - Supports any OpenAI-compatible API endpoint
- **Streamlit Web Interface - Clean UI for recording, displaying, and exporting**
- **Export & Download - Export transcript (.txt) and structured note (.txt / .pdf)**

## **Structured Medical Note Fields**

| **Field** | **Description** |
| --- | --- |
| **Presenting Complaints** | Chief reason for the visit in patient's own words |
| **Symptoms** | Detailed symptom description including onset, duration, severity |
| **Diagnosis** | Provisional or confirmed diagnosis mentioned by physician |
| **Vitals** | Blood pressure, pulse, temperature, respiratory rate, SpO2 |
| **Premorbid Conditions** | Pre-existing chronic conditions, past surgeries, family history |
| **Medication** | Current medications, dosages, new prescriptions issued |
| **Laboratory Tests** | Investigations ordered during the consultation |
| **Consultation Notes** | Free-text clinical reasoning and follow-up instructions |

# **5\. System Architecture**

## **High-Level Architecture**

The system follows a linear pipeline architecture with clean separation between audio capture, transcription, processing, and presentation layers:

\[Microphone Input\]

|

v

\[Audio Capture Module\] ── sounddevice (PCM S16LE, 16kHz, mono)

|

v

\[Transcription Module\] ── Speechmatics WebSocket API (Real-Time, Urdu+EN)

|

v (Partial + Final Transcripts)

\[Transcript Buffer\] ── In-memory + file append (UTF-8)

|

v (on session end / manual trigger)

\[LLM Processing Module\] ── FastAPI server → Ollama / OpenAI-compatible LLM

|

v (Structured JSON / markdown note)

\[Note Formatter\] ── Parse LLM output → 8 structured fields

|

v

\[Streamlit UI Layer\] ── Live transcript panel + Structured note panel

|

v

\[Export Layer\] ── .txt / .pdf download

## **Component Interaction**

| **Component** | **Responsibility** |
| --- | --- |
| **Streamlit UI** | Calls audio module to start/stop recording; displays transcript events; triggers LLM processing; renders structured note |
| **Audio Module** | Streams PCM audio from mic into thread-safe queue; feeds MicStream to Speechmatics client |
| **Transcription Module** | Manages Speechmatics WebSocket; emits partial and final transcript events to UI callback |
| **API Server** | FastAPI endpoint receives transcript JSON; calls LLM; returns structured note JSON |
| **LLM Module** | Constructs medical note prompt; calls Ollama or OpenAI API; returns structured response |
| **Config Manager** | Loads .env variables; provides typed config dataclass to all modules |

# **6\. Technical Architecture**

## **Module Breakdown**

**Audio Capture Module (app/transcription/audio.py)**

Manages microphone input using sounddevice. Implements a thread-safe queue (audio_q) populated by the sounddevice callback. Provides a MicStream class with a read(size) interface compatible with the Speechmatics streaming API. Supports configurable sample rate, channels, and dtype.

**Transcription Module (app/transcription/transcriber.py)**

Wraps the Speechmatics WebsocketClient. Registers event handlers for AddPartialTranscript and AddTranscript. Exposes callbacks to the Streamlit session state for real-time UI updates. Manages connection lifecycle (connect, disconnect, error recovery).

**LLM Module (app/llm/processor.py)**

Builds a structured prompt for the LLM using the full transcript text. Sends POST request to the configured LLM endpoint. Parses the LLM response and maps it to the 8 required medical note fields. Implements retry logic and timeout handling.

**API Layer (server.py using FastAPI)**

Provides a /process endpoint accepting JSON with a transcript field. Calls the LLM module and returns structured_note JSON. Optionally provides a /health endpoint for monitoring. Runs independently of Streamlit on a configurable port.

**UI Layer (app/ui/streamlit_app.py)**

Single-page Streamlit application. Uses st.session_state to manage recording state, transcript buffer, and structured note. Left panel shows live transcript; right panel shows structured medical note. Buttons trigger audio start/stop and LLM processing.

## **Technology Stack**

| **Layer** | **Technology** |
| --- | --- |
| **Frontend UI** | Streamlit 1.35+ |
| **Backend Server** | FastAPI + Uvicorn |
| **Speech Recognition** | Speechmatics Real-Time API (WebSocket) |
| **Audio Capture** | sounddevice (PortAudio backend) |
| **LLM Processing** | Ollama (local) or any OpenAI-compatible API |
| **Urdu Rendering** | arabic-reshaper + python-bidi |
| **HTTP Client** | httpx / requests |
| **Config Management** | python-dotenv + Pydantic BaseSettings |
| **Packaging** | Docker + docker-compose |
| **Testing** | pytest + pytest-asyncio |

# **7\. GitHub Project Folder Structure**

docscribe/

│

├── app/

│ ├── transcription/

│ │ ├── \__init_\_.py

│ │ ├── audio.py # MicStream, audio_callback, queue management

│ │ ├── transcriber.py # Speechmatics WebSocket client wrapper

│ │ └── models.py # Dataclasses for transcript events

│ │

│ ├── llm/

│ │ ├── \__init_\_.py

│ │ ├── processor.py # LLM API call, prompt builder, response parser

│ │ └── prompts.py # System and user prompt templates

│ │

│ ├── api/

│ │ ├── \__init_\_.py

│ │ └── routes.py # FastAPI router: /process, /health

│ │

│ ├── utils/

│ │ ├── \__init_\_.py

│ │ ├── urdu_text.py # arabic-reshaper + bidi rendering utilities

│ │ ├── file_utils.py # Save transcript, export note to .txt/.pdf

│ │ └── logger.py # Structured logging config

│ │

│ └── ui/

│ ├── \__init_\_.py

│ └── components.py # Reusable Streamlit UI components

│

├── streamlit_app.py # Main Streamlit entry point

├── server.py # FastAPI + Uvicorn entry point

│

├── config/

│ ├── settings.py # Pydantic settings model

│ └── .env.example # Template environment file

│

├── docs/

│ ├── architecture.md # Architecture diagram and explanation

│ ├── api.md # API endpoint documentation

│ └── screenshots/ # UI screenshots for README

│

├── tests/

│ ├── test_audio.py

│ ├── test_transcriber.py

│ ├── test_llm.py

│ └── test_api.py

│

├── docker/

│ ├── Dockerfile

│ └── docker-compose.yml

│

├── requirements.txt

├── requirements-dev.txt

├── .env.example

├── README.md

└── LICENSE

# **8\. Streamlit UI Design**

## **Page Layout**

The application is a single-page Streamlit app with a responsive two-column layout. The left column (60% width) contains the live transcription panel. The right column (40% width) contains the structured note panel. A top control bar spans the full width.

## **Control Bar (Top)**

- App title: DocScribe with a microphone icon
- Start Recording button - triggers audio capture + Speechmatics connection
- Stop & Generate Note button - stops recording, sends transcript to LLM, renders note
- Session status indicator - LIVE (green), PROCESSING (yellow), READY (gray)
- Language selector - Urdu+English / English-only

## **Left Panel - Live Transcript**

- Scrollable text area showing transcript lines in real-time
- Partial transcripts shown in gray italic; final transcripts in black
- Urdu text rendered right-to-left with proper shaping
- Timestamps shown next to each finalized line
- Clear Transcript button
- Copy to Clipboard button

## **Right Panel - Structured Medical Note**

- Displayed as collapsible sections, one per medical note field
- Each section has a field icon (e.g., stethoscope for Diagnosis)
- Fields populate progressively as LLM streams response
- Edit mode - allow physician to manually correct any field
- Export buttons - Download as .txt, Download as .pdf
- Copy Note button - copies all fields as formatted markdown

## **UI State Machine**

| **State** | **Description** |
| --- | --- |
| **IDLE** | App loaded, no recording. Start button visible. |
| **RECORDING** | Audio streaming, partial transcripts displayed. Stop button active. |
| **PROCESSING** | Spinner shown, LLM call in progress. Both buttons disabled. |
| **NOTE_READY** | Structured note displayed. Export buttons visible. Can start new session. |
| **ERROR** | Error message shown with retry option. |

# **9\. Data Flow**

## **Full Session Data Flow**

- Doctor opens the Streamlit app in browser (<http://localhost:8501>)
- Doctor clicks Start Recording - Streamlit calls the audio module to open a sounddevice InputStream
- Audio callback fires for each audio chunk, placing PCM bytes into audio_q
- MicStream.read() drains the queue and feeds bytes to the Speechmatics WebSocket client
- Speechmatics processes audio and emits AddPartialTranscript events - displayed in real-time in the UI
- On each AddTranscript (final) event, the transcript line is appended to session buffer and saved to transcript file
- Doctor clicks Stop & Generate Note - audio stream stops, WebSocket closes cleanly
- Streamlit sends the full transcript text via POST to the FastAPI /process endpoint
- FastAPI server receives the request and calls the LLM module
- LLM module builds a structured medical note prompt with the transcript and sends to Ollama/OpenAI API
- LLM returns a structured JSON response with all 8 medical note fields
- FastAPI returns the structured note JSON to Streamlit
- Streamlit renders each field in the right panel; physician reviews and optionally edits
- Doctor clicks Export - note saved as .txt and/or .pdf to local disk

# **10\. Security Considerations**

## **API Key Management**

- All API keys (Speechmatics, OpenAI) stored exclusively in .env file - never hardcoded
- .env file must be listed in .gitignore before first commit
- Provide .env.example with placeholder values and documentation
- Support environment variable injection for Docker and cloud deployments

## **PHI and HIPAA Awareness**

_DocScribe processes Protected Health Information (PHI). While the open-source project itself does not implement full HIPAA compliance, teams deploying it in clinical settings must ensure their deployment environment, LLM provider, and data storage meet applicable regulations._

- Transcript files saved locally - no cloud upload without explicit configuration
- Option to disable file saving for ephemeral in-memory only sessions
- Do not log full transcript content to stdout in production mode
- Structured notes should not be transmitted to untrusted LLM endpoints without TLS
- Add disclaimer in README: This tool is a clinical aid, not a certified medical device

## **Endpoint Security**

- FastAPI server should bind to localhost (127.0.0.1) by default, not 0.0.0.0
- Add optional API token authentication for the /process endpoint
- Rate limiting on the /process endpoint to prevent abuse
- Input validation on transcript field length and content

# **11\. Configuration Management**

## **.env File Variables**

\# Speechmatics Configuration

SPEECHMATICS_API_KEY=your_api_key_here

SPEECHMATICS_URL=wss://eu2.rt.speechmatics.com/v2

SPEECHMATICS_LANGUAGE=ur

\# Audio Configuration

AUDIO_SAMPLE_RATE=16000

AUDIO_CHANNELS=1

\# LLM Backend Configuration

LLM_ENDPOINT=<http://localhost:11434/api/chat>

LLM_MODEL=mistral

LLM_TIMEOUT=120

\# Server Configuration

API_HOST=127.0.0.1

API_PORT=8000

\# File Output

TRANSCRIPT_OUTPUT_DIR=./outputs/transcripts

NOTES_OUTPUT_DIR=./outputs/notes

ENABLE_FILE_SAVING=true

\# Logging

LOG_LEVEL=INFO

LOG_FILE=./logs/docscribe.log

## **Pydantic Settings Model**

All configuration is loaded through a Pydantic BaseSettings class in config/settings.py, providing type safety, validation, and automatic environment variable binding. Components receive a typed Settings object rather than reading os.environ directly.

# **12\. Error Handling**

| **Error Scenario** | **Handling Strategy** |
| --- | --- |
| **Microphone not found** | Catch sounddevice.PortAudioError; display device list in UI; prompt user to select input device |
| **Speechmatics 401** | Catch HTTPStatusError with status 401; display 'Invalid API Key' message with link to config docs |
| **Speechmatics connection drop** | Implement exponential backoff reconnection (max 3 retries); notify user if reconnection fails |
| **LLM timeout** | Set configurable timeout (default 120s); display timeout warning; allow retry with same transcript |
| **LLM malformed response** | Validate JSON structure; fall back to raw text display if parsing fails; log raw response |
| **Empty transcript** | Prevent LLM call if transcript is empty; show 'No transcript recorded' warning |
| **File write error** | Catch IOError; show warning in UI but do not crash session; transcript available in memory |
| **Network error (general)** | Catch requests.ConnectionError; display connection error panel with retry button |

# **13\. Performance Considerations**

## **Transcription Latency**

- Partial transcripts should appear within 1-2 seconds of speech using Speechmatics enhanced mode
- Set max_delay=4 with max_delay_mode=flexible for optimal latency/accuracy balance
- Audio queue should not grow unbounded - implement queue monitoring and drop policy under load

## **LLM Processing**

- Local Ollama inference on a modern CPU (8-core): expect 15-40 seconds for a 10-minute consultation
- GPU-accelerated Ollama (cloud A100): expect 3-8 seconds for the same input
- OpenAI API (gpt-4o): expect 5-15 seconds depending on token count
- Implement streaming LLM responses (stream=true) for progressive note display rather than waiting for full response

## **Streamlit Efficiency**

- Use st.session_state to prevent full page re-renders on transcript updates
- Use st.empty() placeholder for real-time transcript updates (avoids appending new elements each second)
- Audio processing runs in a background thread; Streamlit callbacks must be thread-safe
- Transcript file I/O is synchronous by default - consider async writes for high-frequency sessions

# **14\. Deployment Options**

## **Option 1: Local Development**

\# 1. Clone repository

git clone <https://github.com/aitessam/doc_scribe.git>

cd doc_scribe

\# 2. Create virtual environment

python -m venv venv

source venv/bin/activate # Windows: venv\\Scripts\\activate

\# 3. Install dependencies

pip install -r requirements.txt

\# 4. Configure environment

cp .env.example .env

\# Edit .env with your Speechmatics API key and LLM endpoint

\# 5. Start the FastAPI backend

python server.py

\# 6. Start the Streamlit frontend (new terminal)

streamlit run streamlit_app.py

## **Option 2: Docker Deployment**

\# docker-compose.yml

version: '3.8'

services:

backend:

build: .

command: python server.py

env_file: .env

ports:

\- "8000:8000"

frontend:

build: .

command: streamlit run streamlit_app.py --server.port 8501

env_file: .env

ports:

\- "8501:8501"

depends_on:

\- backend

ollama:

image: ollama/ollama

ports:

\- "11434:11434"

volumes:

\- ollama_models:/root/.ollama

volumes:

ollama_models:

## **Option 3: Cloud GPU Host**

- Rent a GPU instance (A100 recommended for fast LLM inference) from a cloud GPU provider
- Use the Docker template - install Docker on the instance and run docker-compose up
- Point LLM_ENDPOINT in .env at the GPU host's Ollama endpoint
- Forward port 8501 for Streamlit UI access from local browser
- A GPU host provides approximately 10x faster LLM inference vs local CPU for Mistral-7B

# **15\. Future Enhancements**

## **Near-Term (v1.1 - v1.2)**

- Speaker Diarization - Automatically label lines as DOCTOR or PATIENT using Speechmatics diarization feature
- Streaming LLM Output - Display structured note fields progressively as LLM generates them
- Session History - Save and reload past consultations within the UI
- Copy as PDF - One-click export of structured note as a formatted PDF

## **Medium-Term (v2.0)**

- Medical Entity Extraction - NER pipeline to highlight medications, diagnoses, and tests in the transcript
- ICD-10 Code Suggestion - LLM suggests ICD-10 codes based on the diagnosis field
- Browser-Based Recording - WebRTC audio capture to eliminate dependency on local microphone access
- Multi-Language Support - Extend to Arabic, Hindi, Punjabi, and other South Asian languages

## **Long-Term (v3.0)**

- EHR Integration - HL7 FHIR-compatible export for integration with OpenMRS, Bahmni, and commercial EHR systems
- Voice Commands - Doctor can trigger section edits and exports via voice ('Correct diagnosis', 'Export note')
- Fine-Tuned Medical LLM - Fine-tune a domain-specific model on Urdu+English medical conversations
- Clinic Dashboard - Multi-session analytics dashboard for clinic administrators

# **Appendix A: Engineering Guidelines**

## **Code Architecture Principles**

- Modular by default - each module has a single responsibility matching the folder structure in Section 7
- Use Python type hints on all function signatures (PEP 484)
- All public functions and classes must have Google-style docstrings
- No hardcoded values - all configurable parameters must come from Settings object
- Use structured logging (Python logging module) - never print() in production code

## **Testing Strategy**

- Unit tests in tests/ directory using pytest
- Mock external API calls (Speechmatics, LLM) in tests - do not make real API calls in CI
- Target >80% code coverage for core modules (audio, transcriber, llm, api)
- Integration test for the full pipeline using a pre-recorded audio fixture

## **Conventions**

| **Guideline** | **Detail** |
| --- | --- |
| **Naming Convention** | snake_case for files and functions; PascalCase for classes |
| **Error Pattern** | Raise custom exceptions from app/utils/exceptions.py; catch at API/UI boundary |
| **Async Pattern** | Use async/await in FastAPI routes; synchronous code in Streamlit callbacks |
| **LLM Prompt Location** | All prompts in app/llm/prompts.py as module-level constants - never inline |