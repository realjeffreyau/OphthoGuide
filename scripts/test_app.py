"""End-to-end checks of the Streamlit demo (app.py) with Streamlit's AppTest.

Runs the real app script and the real model (a few minutes):
  1. ordinary question with B*  -> answer, sources, passages shown == passages in prompt
  2. unsupported question with B -> withheld/no-evidence handling, still consistent
  3. urgent question with D*    -> urgent notice shown first
  4. version switch D -> B      -> no exception, adapter swapped
  5. missing adapter (env override) -> clear error, no crash

  .venv/bin/python scripts/test_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
MATCH = "Displayed passages match the prompt"


def ask(at: AppTest, version: str, question: str) -> AppTest:
    at.sidebar.radio[0].set_value(version)
    at.text_area[0].input(question)
    at.button[0].click()  # the form's submit button
    return at.run()


def texts(elements) -> list[str]:
    return [e.value for e in elements]


def check(name: str, cond: bool, detail: str = "") -> bool:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    return cond


def main() -> int:
    ok = True
    at = AppTest.from_file(APP, default_timeout=600).run()
    ok &= check("app loads without exception", not at.exception, str(at.exception))

    at = ask(at, "B*", "What is glaucoma?")
    caps = texts(at.caption)
    ok &= check("1 B*: no exception", not at.exception, str(at.exception))
    ok &= check("1 B*: passages match prompt", any(c.startswith("✓ " + MATCH) for c in caps), str(caps))
    ok &= check("1 B*: sources listed", any("**Sources**" in m for m in texts(at.markdown)))
    ok &= check("1 B*: passages expanders present", len(at.expander) >= 2)

    at = ask(at, "B", "How much does LASIK cost?")
    caps = texts(at.caption)
    ok &= check("2 B unsupported: no exception", not at.exception, str(at.exception))
    ok &= check("2 B unsupported: passages match prompt", any(c.startswith("✓ " + MATCH) for c in caps), str(caps))

    at = ask(at, "D*", "I suddenly see flashes and a curtain over my vision. What should I do?")
    errs = texts(at.error)
    ok &= check("3 D* urgent: no exception", not at.exception, str(at.exception))
    ok &= check("3 D* urgent: urgent notice shown", any("Safety notice" in e for e in errs), str(errs))
    ok &= check("3 D* urgent: passages match prompt",
                any(c.startswith("✓ " + MATCH) for c in texts(at.caption)))

    at = ask(at, "D", "What causes dry eye?")
    ok &= check("4a D raw: no exception, adapter used", not at.exception
                and any("adapter: adapters/selected" in c for c in texts(at.caption)))
    at = ask(at, "B", "What causes dry eye?")
    ok &= check("4b switch to B: no exception, no adapter", not at.exception
                and any("adapter: none" in c for c in texts(at.caption)))

    os.environ["OPHTHOGUIDE_ADAPTER"] = str(ROOT / "adapters" / "does_not_exist")
    try:
        at2 = AppTest.from_file(APP, default_timeout=600).run()
        at2 = ask(at2, "D", "What is a cataract?")
        errs = texts(at2.error)
        ok &= check("5 missing adapter: clear error, no exception",
                    not at2.exception and any("Adapter not found" in e for e in errs), str(errs))
    finally:
        del os.environ["OPHTHOGUIDE_ADAPTER"]

    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
