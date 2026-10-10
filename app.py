"""OphthoGuide chat demo.

    .venv/bin/streamlit run app.py

A multi-turn conversation about eye health, grounded in National Eye Institute passages.
The conversation layer is scripts/chat.py on top of the security-hardened assistant
(scripts/assistant.py). The original single-turn evaluated assistant is archived as text;
data/results/FROZEN_CONFIG.json describes that historical snapshot.

Conversations live only in this browser session's memory; nothing is written to disk.
"""
from __future__ import annotations

import copy
import os
import sys
import threading
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

import chat  # noqa: E402
from assistant import MODEL_ID  # noqa: E402

# Overridable so the missing-adapter error path can be tested.
ADAPTER_DIR = Path(os.environ.get("OPHTHOGUIDE_ADAPTER", ROOT / "adapters" / "selected"))
MODEL_REVISION = "52a5ab34fa604bc8af6d3ce0cac0cab10b7eb495"
NEI_CREDIT = "Courtesy: National Eye Institute, National Institutes of Health (NEI/NIH)."
MAX_QUESTION_CHARS = 2000

VERSIONS = {  # name: (label, description)
    "B*": ("B* — base model + retrieval + safeguards",
           "Default (best in the single-turn evaluation). Retrieval, claim verifier, urgent-care notice."),
    "D*": ("D* — fine-tuned + retrieval + safeguards",
           "LoRA adapter with the same safeguards. It did not beat B* in the single-turn evaluation."),
    "B": ("B — base model + retrieval (raw)", "Model output only: no claim verifier, no urgent notice."),
    "D": ("D — fine-tuned + retrieval (raw)", "Model output only, with the LoRA adapter."),
    "A": ("A — base model, no retrieval (raw)", "No passages. For comparison only."),
    "C": ("C — fine-tuned, no retrieval (raw)", "Least safe in testing. For comparison only."),
}


@st.cache_resource
def generation_lock() -> threading.Lock:
    """One process-wide lock: one generation at a time, one model configuration in memory."""
    return threading.Lock()


def new_chat() -> None:
    st.session_state.messages = []
    st.session_state.ctx = chat.PatientContext()
    st.session_state.conv_id = uuid.uuid4().hex[:12]
    st.session_state.pop("last_error", None)


def validate(message: str) -> str:
    if not message or not message.strip() or len(message) > MAX_QUESTION_CHARS:
        raise ValueError(f"Enter a message of 1–{MAX_QUESTION_CHARS} characters.")
    return message.strip()


def run_turn(message: str, version: str, messages: list[dict], ctx: chat.PatientContext,
             conv_id: str, style: str = "explain") -> dict:
    """One assistant turn. Raises ValueError for bad input before any model work."""
    message = validate(message)
    uses_adapter = chat.VERSIONS[version][0]
    if uses_adapter and not (ADAPTER_DIR / "adapters.safetensors").exists():
        raise FileNotFoundError("adapter missing")
    with generation_lock():
        return chat.respond(message, messages, ctx, version, str(ADAPTER_DIR), conv_id, style)


def show_assistant(m: dict, show_prompt: bool) -> None:
    if m["urgent"] and m["safeguards"]:
        st.error(chat.URGENT_NOTICE)
    if not m["safeguards"]:
        st.caption("⚠ Raw model output for comparison — no claim verifier, no urgent-care notice.")
    text, sources = chat.render_citations(m["content"], m["results"])
    st.markdown(text)
    if m["citations"]["invalid"]:
        st.caption("⚠ ˀ marks a cited passage ID that was not supplied to the model: "
                   + ", ".join(m["citations"]["invalid"]))
    if m.get("general"):
        st.caption("Sentences without a source number are the AI's general explanation, not checked "
                   "against the NEI pages, and may contain errors.")
    adapter = os.path.relpath(m["adapter"], ROOT) if m["adapter"] else "none"
    style = "explain" if m.get("style", "strict") == "explain" else "strict sources"
    st.caption(f"Answered by {m['version']} · {style} · adapter: {adapter} · {m['seconds']:.0f} s")

    with st.expander(f"Sources ({len(sources)})" if sources else "Evidence details"):
        for i, r in enumerate(sources, 1):
            upd = f" · updated {r['updated']}" if r.get("updated") else ""
            st.markdown(f"**{i}. [{r['title']} — {r['section']}]({r['url']})**{upd}")
            st.text(r["text"])
        if not m["results"]:
            if m["weak"]:
                st.markdown("No passage covered this well enough, so the model was told it had **no usable "
                            "evidence**. Retrieval had found: "
                            + (", ".join(r["chunk_id"] for r in m["retrieved"]) or "nothing"))
            else:
                st.markdown("Retrieval is off for this version: no passages were supplied.")
        unused = [r["chunk_id"] for r in m["results"] if r not in sources]
        if unused:
            st.caption("Also supplied but not cited: " + ", ".join(unused))
        if m["partial"]:
            st.markdown("**◐ Partly supported** — the source's own wording:")
            for c in m["partial"]:
                st.caption(f"“{c['quote']}” [{c['id']}]")
        if m.get("general"):
            st.markdown("**General explanation** (not from the NEI pages):")
            for g in m["general"]:
                st.caption("◇ " + g)
        if m["removed"]:
            st.markdown("**Removed because the sources contradict them or do not support them:**"
                        if m.get("style") == "explain" else
                        "**Removed because the sources do not support them:**")
            for c in m["removed"]:
                st.caption("✗ " + c["claim"])
        if m["caveats"]:
            st.markdown("**Source caveats** (verbatim, not covered above):")
            for c in m["caveats"]:
                st.caption(f"{c['text']} [{c['id']}]")
        st.caption(f"Search query: {m['query']}" + (" · new topic" if m["topic_changed"] else ""))
        if show_prompt:
            st.code(m["prompt"], language=None)


def main() -> None:
    st.set_page_config(page_title="OphthoGuide", page_icon="👁", layout="centered")
    if "messages" not in st.session_state:
        new_chat()

    with st.sidebar:
        st.header("OphthoGuide")
        if st.button("New chat", icon="➕", use_container_width=True):
            new_chat()
        st.subheader("Model version")
        version = st.radio("Model version", list(VERSIONS), format_func=lambda v: VERSIONS[v][0],
                           index=0, label_visibility="collapsed")
        st.caption(VERSIONS[version][1])
        strict = st.toggle("Strict: sources only", value=False,
                           help="Off: explains possibilities, using NEI pages where they apply and general "
                                "knowledge otherwise (marked). On: only statements the NEI pages support.")
        show_prompt = st.toggle("Show exact prompt", value=False)
        st.subheader("What you've told me")
        lines = st.session_state.ctx.lines()
        for line in lines:
            st.caption("• " + line)
        st.caption("Only what you wrote — never the assistant's suggestions. To correct something, "
                   "just say so (e.g. “actually, my left eye”)." if lines else "Nothing yet.")
        st.caption("This conversation is kept only in this browser session and is not saved.")
        with st.expander("How well does it work?"):
            st.markdown(
                "- **Single-turn test** (150 cases, blinded, AI-scored, no clinician review): retrieval roughly "
                "doubled correctness; fine-tuning did not improve it; no version met the "
                "zero-urgent-failure criterion.\n"
                "- **Multi-turn chat test**: see `data/evaluation_chat/RESULTS.md`.")

    st.title("👁 OphthoGuide")
    st.caption("An AI learning tool for eye health. It suggests possibilities and explains them, using "
               "National Eye Institute pages where they apply — it **can make mistakes** and is not a "
               "diagnosis. For sudden vision changes, an eye injury, or severe eye pain, see an eye doctor "
               "or go to the emergency room now.")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                show_assistant(m, show_prompt)

    prompt = st.chat_input("Describe what's happening with your eyes, or ask a question",
                           max_chars=MAX_QUESTION_CHARS)
    if prompt is not None:
        if not prompt.strip():
            st.warning("Please type a message.")
        else:
            with st.chat_message("user"):
                st.markdown(prompt)
            # Work on a copy so a failed turn leaves the conversation and context untouched.
            ctx = copy.deepcopy(st.session_state.ctx)
            error = None
            with st.chat_message("assistant"), st.spinner(f"Thinking ({version})…"):
                try:
                    reply = run_turn(prompt, version, st.session_state.messages, ctx,
                                     st.session_state.conv_id, "strict" if strict else "explain")
                except FileNotFoundError:
                    error = ("The fine-tuned adapter is missing. Train and select one "
                             "(scripts/select_checkpoint.py) or choose a base-model version.")
                except ValueError:
                    error = f"Enter a message of 1–{MAX_QUESTION_CHARS} characters."
                except Exception:  # model load/generation failure; details stay out of the UI
                    error = ("The model could not be loaded or run. Check the local setup in README.md "
                             "and try again.")
            if error:
                st.session_state.last_error = error
            else:
                st.session_state.ctx = ctx
                st.session_state.messages.append({"role": "user", "content": prompt.strip(),
                                                  "topic_start": reply["topic_changed"]})
                st.session_state.messages.append(reply)
                st.session_state.pop("last_error", None)
            st.rerun()
    if st.session_state.get("last_error"):
        st.error(st.session_state.last_error)

    st.caption(NEI_CREDIT + f" · {MODEL_ID} @ {MODEL_REVISION[:8]}")


main()
