"""End-to-end checks of the Streamlit chat (app.py) with Streamlit's AppTest and the real model.

Covers: a first question with sources, a short follow-up linked to the earlier complaint,
a correction, a new symptom that makes the conversation urgent, switching model versions
(label + adapter per message), New chat clearing history and patient context, and a
missing adapter. Takes several minutes.

  .venv/bin/python scripts/test_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
FAILS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global FAILS
    FAILS += not cond
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + ("" if cond else f" — {detail}"), flush=True)


def say(at: AppTest, text: str, version: str | None = None) -> AppTest:
    if version:
        at.sidebar.radio[0].set_value(version)
    at.chat_input[0].set_value(text)
    return at.run()


def captions(at: AppTest) -> list[str]:
    return [c.value for c in at.caption] + [c.value for c in at.sidebar.caption]


def main() -> int:
    at = AppTest.from_file(APP, default_timeout=900).run()
    check("app loads", not at.exception, str(at.exception))
    check("default version is B*", at.sidebar.radio[0].value == "B*")

    at = say(at, "My right eye has been blurry and a bit red.")
    check("turn 1: no exception", not at.exception, str(at.exception))
    check("turn 1: two chat messages", len(at.chat_message) == 2, str(len(at.chat_message)))
    check("turn 1: labelled with version", any("Answered by B*" in c for c in captions(at)))
    check("turn 1: sources expander", any(e.label.startswith(("Sources", "Evidence")) for e in at.expander))
    check("turn 1: context panel shows the reported eye", any("Eye: right eye" in c for c in captions(at)))

    at = say(at, "Two days. No pain.")
    caps = captions(at)
    check("follow-up: timing remembered", any("Timing: 2 days" in c for c in caps), str(caps))
    check("follow-up: denial remembered", any("do NOT have: eye pain" in c for c in caps))
    check("follow-up: search used the earlier complaint", any("Search query:" in c and "blurry" in c for c in caps))

    at = say(at, "Actually, it's my left eye, not the right.")
    check("correction: eye updated with history", any("Eye: left eye (corrected from right eye)" in c
                                                      for c in captions(at)), str(captions(at)))

    at = say(at, "Now I suddenly see flashes and a dark curtain over part of my vision.")
    errs = [e.value for e in at.error]
    check("new symptom: urgent notice shown", any("Safety notice" in e for e in errs), str(errs))

    at = say(at, "What is glaucoma?", version="D*")
    caps = captions(at)
    check("switch: newest reply labelled D*", any("Answered by D* · explain · adapter: adapters/selected" in c for c in caps))
    check("switch: older replies keep their label", any("Answered by B* · explain · adapter: none" in c for c in caps))
    at = say(at, "How is it treated?", version="B*")
    check("switch back: reply labelled B* with no adapter",
          [c for c in captions(at) if c.startswith("Answered by")][-1].startswith("Answered by B* · explain · adapter: none"))

    at.sidebar.button[0].click()
    at = at.run()
    check("new chat: history cleared", len(at.chat_message) == 0, str(len(at.chat_message)))
    check("new chat: patient context cleared", any(c == "Nothing yet." for c in captions(at)))

    os.environ["OPHTHOGUIDE_ADAPTER"] = str(ROOT / "adapters" / "does_not_exist")
    try:
        at2 = AppTest.from_file(APP, default_timeout=600).run()
        at2 = say(at2, "What is a cataract?", version="D")
        errs = [e.value for e in at2.error]
        check("missing adapter: clear error, no crash, nothing added",
              not at2.exception and any("adapter is missing" in e for e in errs) and len(at2.chat_message) == 0,
              str(errs))
    finally:
        del os.environ["OPHTHOGUIDE_ADAPTER"]

    print("ALL PASS" if not FAILS else f"{FAILS} FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
