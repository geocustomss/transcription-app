import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest


class TranscriptionAppTests(unittest.TestCase):
    @patch("src.cleanup.httpx.post")
    def test_typed_input_creates_one_automatically_cleaned_transcript(self, post):
        response = Mock()
        response.json.return_value = {"response": "A cleaned transcript."}
        post.return_value = response

        app = AppTest.from_file("../app.py")
        app.session_state["input_mode"] = "Type or paste"
        app.run()
        app.text_area(key="typed_input").set_value("a rough transcript").run()
        app.button[0].click().run()

        self.assertFalse(app.exception)
        self.assertEqual(app.button[0].label, "Create transcript")
        self.assertEqual(app.text_area(key="edited_text").value, "A cleaned transcript.")
        self.assertEqual(len(app.download_button), 1)
        post.assert_called_once()


if __name__ == "__main__":
    unittest.main()