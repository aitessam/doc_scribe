import os
import tempfile
from pathlib import Path

# Settings are read at import time, so the environment must be prepared first.
os.environ.setdefault("SPEECHMATICS_API_KEY", "test-key")
os.environ.setdefault("LOG_FILE", str(Path(tempfile.gettempdir()) / "docscribe-test.log"))
os.environ.setdefault("LLM_ENDPOINT", "http://localhost:11434/api/chat")
