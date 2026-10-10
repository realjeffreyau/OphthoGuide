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


class DemoSecurityTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def submit(self, app, question):
        app.sidebar.radio[0].set_value("B")
        app.text_area[0].input(question)
        app.button[0].click()
        return app.run()

    def test_server_defaults(self):
        config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text())
        self.assertEqual(config["server"]["address"], "127.0.0.1")
        self.assertTrue(config["server"]["enableCORS"])
        self.assertTrue(config["server"]["enableXsrfProtection"])
        self.assertFalse(config["browser"]["gatherUsageStats"])

    def test_blank_input_never_generates(self):
        with patch.object(assistant, "generate_answer") as generate:
            app = self.submit(self.app(), "   ")
        generate.assert_not_called()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)

    def test_oversized_input_never_generates(self):
        spec = importlib.util.spec_from_file_location("ophthoguide_app", ROOT / "app.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(assistant, "generate_answer") as generate:
            with self.assertRaises(ValueError):
                module.run("x" * 2001, "B")
        generate.assert_not_called()

    def test_internal_error_is_not_displayed(self):
        private_message = "PRIVATE_TEST_PATH_AND_CREDENTIAL"
        with patch.object(assistant, "configure"), \
             patch.object(assistant, "retrieve_evidence", return_value=([], False)), \
             patch.object(assistant, "generate_answer", side_effect=RuntimeError(private_message)):
            app = self.submit(self.app(), "What is glaucoma?")
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn(private_message, " ".join(e.value for e in app.error))


if __name__ == "__main__":
    unittest.main()
