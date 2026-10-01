from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {
    ".aac",
    ".avi",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
    ".wma",
}
MAX_MEDIA_BYTES = 100 * 1024 * 1024
MAX_MEDIA_SECONDS = 30 * 60
SAMPLE_RATE = 16_000


class MediaInputError(ValueError):
    pass


class TranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    language: str | None
    duration_seconds: float


def validate_media(
    filename: str,
    data: bytes,
    max_bytes: int = MAX_MEDIA_BYTES,
) -> None:
    if not data:
        raise MediaInputError("The selected recording is empty.")
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise MediaInputError(f"Unsupported file type. Choose one of: {allowed}.")
    if len(data) > max_bytes:
        raise MediaInputError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")


def decode_audio(data: bytes) -> Any:
    try:
        import av
        import numpy as np

        with av.open(io.BytesIO(data), mode="r") as container:
            audio_streams = container.streams.audio
            if not audio_streams:
                raise MediaInputError("This file does not contain an audio track.")

            stream = audio_streams[0]
            if container.duration is not None:
                duration = container.duration / av.time_base
                if duration > MAX_MEDIA_SECONDS:
                    raise MediaInputError("Recordings must be 30 minutes or shorter.")

            resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
            chunks: list[Any] = []
            sample_count = 0
            for frame in container.decode(stream):
                for resampled in resampler.resample(frame):
                    chunk = resampled.to_ndarray().reshape(-1).astype(np.float32, copy=False)
                    sample_count += len(chunk)
                    if sample_count > MAX_MEDIA_SECONDS * SAMPLE_RATE:
                        raise MediaInputError("Recordings must be 30 minutes or shorter.")
                    chunks.append(chunk)
            for resampled in resampler.resample(None):
                chunk = resampled.to_ndarray().reshape(-1).astype(np.float32, copy=False)
                sample_count += len(chunk)
                if sample_count > MAX_MEDIA_SECONDS * SAMPLE_RATE:
                    raise MediaInputError("Recordings must be 30 minutes or shorter.")
                chunks.append(chunk)

        if not chunks:
            raise MediaInputError("No decodable audio was found in this file.")
        return np.concatenate(chunks)
    except MediaInputError:
        raise
    except Exception as error:
        raise MediaInputError("Could not read this media file. Try a WAV, MP3, M4A, MP4, or WebM file.") from error


@lru_cache(maxsize=2)
def load_model(model_name: str = "small") -> Any:
    try:
        from faster_whisper import WhisperModel

        return WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception as error:
        raise TranscriptionError(
            "The local speech model could not be loaded. Check the model download and try again."
        ) from error


def transcribe_media(
    filename: str,
    data: bytes,
    model: Any | None = None,
    model_name: str = "small",
) -> TranscriptResult:
    validate_media(filename, data)
    audio = decode_audio(data)
    duration_seconds = len(audio) / SAMPLE_RATE
    if duration_seconds <= 0:
        raise MediaInputError("No decodable audio was found in this file.")

    speech_model = model if model is not None else load_model(model_name)
    try:
        segments, info = speech_model.transcribe(audio, beam_size=5, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
    except Exception as error:
        raise TranscriptionError("Transcription failed. Try the recording again or use another file.") from error
    if not text:
        raise TranscriptionError("No speech was detected in this recording.")

    return TranscriptResult(
        text=text,
        language=getattr(info, "language", None),
        duration_seconds=duration_seconds,
    )