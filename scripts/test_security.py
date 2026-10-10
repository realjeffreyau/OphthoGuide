"""Demo security regression checks; no model download or inference required."""
from pathlib import Path
import importlib.util
import sys
import tomllib
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import assistant
import chat


class DemoSecurityTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def submit(self, app, question):
        app.sidebar.radio[0].set_value("B")
        app.chat_input[0].set_value(question)
        return app.run()

    def test_server_defaults(self):
        config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text())
        self.assertEqual(config["server"]["address"], "127.0.0.1")
        self.assertTrue(config["server"]["enableCORS"])
        self.assertTrue(config["server"]["enableXsrfProtection"])
        self.assertFalse(config["browser"]["gatherUsageStats"])

    def test_blank_input_never_generates(self):
        with patch.object(chat, "generate_chat") as generate:
            app = self.submit(self.app(), "   ")
        generate.assert_not_called()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)

    def test_oversized_input_never_generates(self):
        spec = importlib.util.spec_from_file_location("ophthoguide_app", ROOT / "app.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(chat, "generate_chat") as generate:
            with self.assertRaises(ValueError):
                module.run_turn("x" * 2001, "B", [], chat.PatientContext(), "t")
        generate.assert_not_called()

    def test_internal_error_is_not_displayed(self):
        private_message = "PRIVATE_TEST_PATH_AND_CREDENTIAL"
        with patch.object(assistant, "configure"), \
             patch.object(chat, "retrieve_evidence", return_value=([], False)), \
             patch.object(chat, "generate_chat", side_effect=RuntimeError(private_message)):
            app = self.submit(self.app(), "What is glaucoma?")
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn(private_message, " ".join(e.value for e in app.error))

    def test_comparison_parser(self):
        cases = {
            "What is the difference between cataracts and glaucoma?": ["cataracts", "glaucoma"],
            "cataracts vs. glaucoma!": ["cataracts", "glaucoma"],
            "compare dry eye with pink eye.": ["dry eye", "pink eye"],
            "comparing dry eye to pink eye?": ["dry eye", "pink eye"],
            "What is glaucoma?": [],
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(assistant.comparison_parts(question), expected)

    def test_comparison_parser_rejects_adversarial_length(self):
        for question in [" " * 1000000, "difference between a and " + "a and a" * 100000,
                         "compare a to a" + "!" * 100000]:
            self.assertEqual(assistant.comparison_parts(question), [])


    def test_model_html_is_not_rendered(self):
        text, _ = chat.render_citations("<script>alert(1)</script> Glaucoma [nei_002_chunk_01].",
                                        [{"chunk_id": "nei_002_chunk_01"}])
        self.assertIn("<script>", text)                     # left as text for Markdown to escape
        src = (ROOT / "app.py").read_text()
        self.assertNotIn("unsafe_allow_html", src)
        self.assertNotIn("st.html", src)


if __name__ == "__main__":
    unittest.main()
