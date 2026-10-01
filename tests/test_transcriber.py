import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from src.transcriber import (
    MediaInputError,
    TranscriptionError,
    transcribe_media,
    validate_media,
)


class FakeModel:
    def transcribe(self, audio, **kwargs):
        return iter([SimpleNamespace(text=" A clear sentence."), SimpleNamespace(text=" And another.")]), SimpleNamespace(language="en")


class TranscriberTests(unittest.TestCase):
    def test_rejects_empty_recording(self):
        with self.assertRaisesRegex(MediaInputError, "empty"):
            validate_media("recording.wav", b"")

    def test_rejects_unsupported_file(self):
        with self.assertRaisesRegex(MediaInputError, "Unsupported file type"):
            validate_media("notes.txt", b"content")

    def test_rejects_oversized_file(self):
        with self.assertRaisesRegex(MediaInputError, "limit"):
            validate_media("recording.wav", b"1234", max_bytes=3)

    @patch("src.transcriber.decode_audio", return_value=np.zeros(16_000, dtype=np.float32))
    def test_transcribes_and_joins_segments(self, _decode_audio):
        result = transcribe_media("recording.wav", b"audio", model=FakeModel())

        self.assertEqual(result.text, "A clear sentence. And another.")
        self.assertEqual(result.language, "en")
        self.assertEqual(result.duration_seconds, 1.0)

    @patch("src.transcriber.decode_audio", return_value=np.zeros(16_000, dtype=np.float32))
    @patch("src.transcriber.load_model", return_value=FakeModel())
    def test_uses_the_configured_model_name(self, load_model, _decode_audio):
        transcribe_media("recording.wav", b"audio", model_name="tiny.en")

        load_model.assert_called_once_with("tiny.en")

    @patch("src.transcriber.decode_audio", return_value=np.zeros(16_000, dtype=np.float32))
    def test_empty_speech_result_is_reported(self, _decode_audio):
        model = SimpleNamespace(transcribe=lambda *_args, **_kwargs: (iter([]), SimpleNamespace(language="en")))

        with self.assertRaisesRegex(TranscriptionError, "No speech"):
            transcribe_media("recording.wav", b"audio", model=model)


if __name__ == "__main__":
    unittest.main()