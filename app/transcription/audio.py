from __future__ import annotations

import queue
from contextlib import contextmanager
from typing import Any, Generator, Optional

import sounddevice as sd

from app.utils.exceptions import AudioCaptureError
from config.settings import AudioConfig, get_settings

# Thread-safe queue of raw PCM audio bytes produced by the sounddevice callback.
audio_q: queue.Queue[bytes] = queue.Queue()

_active_stream: Optional[sd.InputStream] = None


def audio_callback(indata: Any, frames: int, time: Any, status: Any) -> None:
    """Sounddevice input callback that enqueues microphone audio bytes.

    This mirrors the reference pattern: push raw bytes into a global thread-safe
    queue. The Speechmatics streaming client consumes these bytes through the
    `MicStream.read()` interface.

    Args:
        indata: Audio input buffer provided by sounddevice (typically a numpy
            ndarray). Its contents represent PCM samples.
        frames: Number of frames in this callback block.
        time: Timing information provided by sounddevice.
        status: Callback status flags or messages from sounddevice.

    Raises:
        AudioCaptureError: If audio bytes cannot be enqueued.
    """

    try:
        if status:
            # Preserve the "print status" behavior from the reference while using logging
            # later in the app; for now, we keep it non-fatal.
            pass
        audio_q.put(bytes(indata))
    except Exception as exc:  # pragma: no cover - defensive, depends on audio driver
        raise AudioCaptureError("Failed to enqueue audio buffer.", cause=exc) from exc


class MicStream:
    """Queue-backed microphone stream adapter.

    Speechmatics' streaming API expects a file-like object that provides a
    `read(size)` method returning bytes. This implementation pulls from the
    global `audio_q`.
    """

    def read(self, size: int) -> bytes:
        """Read and return the next chunk of microphone audio bytes.

        Note: The reference implementation ignores `size` and returns a single
        queued chunk. We follow the same pattern for compatibility and simplicity.

        Args:
            size: Requested byte size (not enforced).

        Returns:
            bytes: The next queued audio chunk.

        Raises:
            AudioCaptureError: If the queue read fails unexpectedly.
        """

        try:
            return audio_q.get()
        except Exception as exc:  # pragma: no cover
            raise AudioCaptureError("Failed to read audio buffer from queue.", cause=exc) from exc


@contextmanager
def start_stream() -> Generator[MicStream, None, None]:
    """Start microphone capture and yield a `MicStream` for consumers.

    This context manager opens a `sounddevice.InputStream` using audio settings
    from `config/settings.py`, and routes captured PCM samples into `audio_q`
    via `audio_callback`.

    Yields:
        MicStream: A queue-backed stream adapter for downstream transcription.

    Raises:
        AudioCaptureError: If the input stream cannot be started.
    """

    global _active_stream
    settings = get_settings()
    audio_config = AudioConfig(
        sample_rate=settings.AUDIO_SAMPLE_RATE,
        channels=settings.AUDIO_CHANNELS,
        dtype="int16",
    )

    try:
        # Clear any stale buffers before starting a new session.
        while not audio_q.empty():
            try:
                audio_q.get_nowait()
            except queue.Empty:
                break

        stream = sd.InputStream(
            samplerate=audio_config.sample_rate,
            channels=audio_config.channels,
            dtype=audio_config.dtype,
            callback=audio_callback,
        )
        stream.start()
        _active_stream = stream

        yield MicStream()
    except Exception as exc:
        raise AudioCaptureError("Failed to start microphone audio stream.", cause=exc) from exc
    finally:
        stop_stream()


def stop_stream() -> None:
    """Stop and close the active microphone stream and perform cleanup.

    This function is safe to call multiple times.

    Raises:
        AudioCaptureError: If the audio stream cannot be stopped/closed cleanly.
    """

    global _active_stream
    if _active_stream is None:
        return

    try:
        _active_stream.stop()
        _active_stream.close()
    except Exception as exc:  # pragma: no cover - depends on audio driver behavior
        raise AudioCaptureError("Failed to stop/close microphone audio stream.", cause=exc) from exc
    finally:
        _active_stream = None

