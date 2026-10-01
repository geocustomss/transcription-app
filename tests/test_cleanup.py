import unittest
from unittest.mock import Mock, patch

import httpx

from src.cleanup import CleanupError, TRANSCRIPT_CLEANUP_INSTRUCTIONS, cleanup_transcript


class CleanupTests(unittest.TestCase):
    @patch("src.cleanup.httpx.post")
    def test_combines_all_cleanup_steps_in_one_local_request(self, post):
        response = Mock()
        response.json.return_value = {"response": "A single cleaned transcript."}
        post.return_value = response

        result = cleanup_transcript("  Source transcript.  ")

        self.assertEqual(result, "A single cleaned transcript.")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "http://127.0.0.1:11434/api/generate")
        self.assertIn("punctuation", kwargs["json"]["prompt"])
        self.assertIn("remove speech fillers", kwargs["json"]["prompt"])
        self.assertIn("improve readability", kwargs["json"]["prompt"])
        self.assertEqual(kwargs["timeout"], 180)

    def test_cleanup_instructions_combine_requested_edits(self):
        self.assertIn("punctuation", TRANSCRIPT_CLEANUP_INSTRUCTIONS)
        self.assertIn("remove speech fillers", TRANSCRIPT_CLEANUP_INSTRUCTIONS)
        self.assertIn("improve readability", TRANSCRIPT_CLEANUP_INSTRUCTIONS)

    def test_rejects_blank_text_without_network_call(self):
        with patch("src.cleanup.httpx.post") as post:
            with self.assertRaises(ValueError):
                cleanup_transcript("  ")
        post.assert_not_called()

    @patch("src.cleanup.httpx.post", side_effect=httpx.ConnectError("offline"))
    def test_reports_unavailable_local_model(self, _post):
        with self.assertRaisesRegex(CleanupError, "local Ollama"):
            cleanup_transcript("hello")

    @patch("src.cleanup.httpx.post")
    def test_rejects_empty_model_response(self, post):
        response = Mock()
        response.json.return_value = {"response": "  "}
        post.return_value = response

        with self.assertRaisesRegex(CleanupError, "empty result"):
            cleanup_transcript("hello")


if __name__ == "__main__":
    unittest.main()