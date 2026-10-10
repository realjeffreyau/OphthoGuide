"""OphthoGuide local demo.

    .venv/bin/streamlit run app.py

Ask a question, read the answer, inspect exactly which NEI passages the model received,
and compare the evaluated versions (A–D raw model output, B*/D* full pipeline).

The demo uses the security-hardened assistant. The original evaluated assistant is
archived as text; data/results/FROZEN_CONFIG.json describes that historical snapshot.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import threading
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

import assistant  # noqa: E402
from assistant import (MAX_TOKENS, MODEL_ID, SYSTEM_PROMPT, TEMPERATURE, URGENT_NOTICE,  # noqa: E402
                       build_user_message, check_citations, generate_answer, retrieve_evidence)

# Overridable so the missing-adapter error path can be tested.
ADAPTER_DIR = Path(os.environ.get("OPHTHOGUIDE_ADAPTER", ROOT / "adapters" / "selected"))
MODEL_REVISION = "52a5ab34fa604bc8af6d3ce0cac0cab10b7eb495"
NEI_CREDIT = "Courtesy: National Eye Institute, National Institutes of Health (NEI/NIH)."
MAX_QUESTION_CHARS = 2000

# name: (label, uses adapter, uses retrieval, full pipeline, description)
VERSIONS = {
    "B*": ("B* — base model + retrieval + safeguards", False, True, True,
           "Recommended. Retrieval, claim verifier, urgent-care notice, source caveats. "
           "Best overall in the evaluation."),
    "D*": ("D* — fine-tuned + retrieval + safeguards", True, True, True,
           "Same pipeline with the LoRA adapter: shorter, more extractive answers; "
           "weaker at correcting false premises."),
    "B": ("B — base model + retrieval (raw)", False, True, False,
          "Model output only, no verifier or urgent notice."),
    "D": ("D — fine-tuned + retrieval (raw)", True, True, False,
          "Model output only, with the LoRA adapter."),
    "A": ("A — base model, no retrieval (raw)", False, False, False,
          "No passages supplied. Under the grounding prompt it mostly declines."),
    "C": ("C — fine-tuned, no retrieval (raw)", True, False, False,
          "Least safe in testing: it often answered emergencies with questions."),
}


@st.cache_resource
def generation_lock() -> threading.Lock:
    """One process-wide lock: one generation at a time, one model configuration in memory."""
    return threading.Lock()


def question_seed(question: str) -> int:
    return int(hashlib.sha256(question.strip().lower().encode()).hexdigest()[:8], 16)


def run(question: str, version: str) -> dict:
    """Answer with one version. Raises on model/adapter problems (shown by the caller)."""
    if not question.strip() or len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"Enter a question of 1–{MAX_QUESTION_CHARS} characters.")
    _, uses_adapter, uses_retrieval, full, _ = VERSIONS[version]
    if uses_adapter and not (ADAPTER_DIR / "adapters.safetensors").exists():
        raise FileNotFoundError(
            "Adapter not found. Train and select one "
            "(scripts/select_checkpoint.py --run adapters/run_01 --select) or pick a base-model version.")
    seed = question_seed(question)
    with generation_lock():
        # assistant keeps the loaded model in a module global, which survives Streamlit reruns;
        # configure() only reloads when the adapter changes.
        assistant.configure(str(ADAPTER_DIR) if uses_adapter else None)
        t0 = time.perf_counter()
        if full:
            rec = assistant.answer(question, retrieval=True, seed=seed)
            ver = rec.get("verification") or {}
            out = {"answer": rec["answer"], "results": rec["results"], "weak": rec["weak_evidence"],
                   "prompt": rec["prompt"], "citations": rec["citations"],
                   "removed": ver.get("removed", []),
                   "partial": [c for c in ver.get("checks", []) if c["status"] == "partial"],
                   "caveats": rec.get("caveats") or [], "urgent": rec["urgent"]}
        else:
            results, weak = retrieve_evidence(question) if uses_retrieval else ([], False)
            prompt = build_user_message(question, results, weak, uses_retrieval)
            text = generate_answer(SYSTEM_PROMPT, prompt, seed=seed)
            out = {"answer": text, "results": results, "weak": weak, "prompt": prompt,
                   "citations": check_citations(text, results, weak), "removed": [],
                   "partial": [], "caveats": [], "urgent": False}
        out["seconds"] = time.perf_counter() - t0
    out.update(version=version, retrieval=uses_retrieval, full=full, seed=seed,
               adapter=os.path.relpath(ADAPTER_DIR, ROOT) if uses_adapter else None)
    return out


def supplied(out: dict) -> list[dict]:
    """The passages the model actually received (none if retrieval was off or evidence weak)."""
    return [] if (out["weak"] or not out["retrieval"]) else out["results"]


def passages_match_prompt(out: dict) -> bool:
    """Every displayed passage is in the prompt, and no other passage ID is."""
    shown = supplied(out)
    in_prompt = set(re.findall(r"^\[([a-z]+_\d+_chunk_\d+)\]$", out["prompt"], re.M))
    return (in_prompt == {p["chunk_id"] for p in shown}
            and all(p["text"] in out["prompt"] for p in shown))


def show_answer(out: dict) -> None:
    by_id = {r["chunk_id"]: r for r in out["results"]}
    if out["full"] and out["urgent"]:
        st.error(URGENT_NOTICE)
    if not out["full"]:
        st.warning("Raw model output for comparison: no claim verifier, no urgent-care notice.")
    st.markdown(out["answer"])

    cit = out["citations"]
    if cit["valid"]:
        st.markdown("**Sources**")
        for cid in cit["valid"]:
            r = by_id[cid]
            upd = f" (updated {r['updated']})" if r.get("updated") else ""
            st.markdown(f"- `{cid}` [{r['title']} — {r['section']}]({r['url']}){upd}")
    if cit["invalid"]:
        st.error(f"Cited IDs that were not supplied to the model: {', '.join(cit['invalid'])}")
    if out["partial"]:
        with st.expander(f"◐ Partly supported statements ({len(out['partial'])})"):
            for c in out["partial"]:
                st.markdown(f"- “{c['claim']}” — source says [{c['id']}]: “{c['quote']}”")
    if out["removed"]:
        with st.expander(f"Removed as unsupported by the sources ({len(out['removed'])})"):
            for c in out["removed"]:
                st.markdown(f"- ~~{c['claim']}~~")
    if out["caveats"]:
        st.markdown("**Source caveats** (verbatim from the cited pages, not covered above)")
        for c in out["caveats"]:
            st.markdown(f"> {c['text']} `[{c['id']}]`")


def show_evidence(out: dict, show_prompt: bool) -> None:
    st.divider()
    shown = supplied(out)
    if not out["retrieval"]:
        st.info("Retrieval is off for this version: no passages were supplied to the model.")
    elif out["weak"]:
        st.info("Evidence withheld: no passage covered enough of the question, so the model was "
                "told NO USABLE EVIDENCE. Retrieval had found:")
        for r in out["results"]:
            st.caption(f"{r['chunk_id']} — {r['title']} › {r['section']} (coverage {r.get('coverage')})")
    else:
        st.markdown(f"**Passages supplied to the model ({len(shown)})**")
        for r in shown:
            upd = f" · updated {r['updated']}" if r.get("updated") else ""
            with st.expander(f"{r['chunk_id']} — {r['title']} › {r['section']}"):
                st.markdown(f"[{r['url']}]({r['url']}){upd}")
                st.text(r["text"])
    ok = passages_match_prompt(out)
    st.caption(("✓ " if ok else "✗ ") + "Displayed passages match the prompt sent to the model.")
    if show_prompt:
        with st.expander("Exact prompt (user message) sent to the model"):
            st.code(out["prompt"], language=None)
    st.caption(f"{out['seconds']:.1f} s · {MODEL_ID} @ {MODEL_REVISION[:8]} · adapter: "
               f"{out['adapter'] or 'none'} · temp {TEMPERATURE}, top_p 0.9, max {MAX_TOKENS} "
               f"tokens · seed {out['seed']}")
    st.caption(NEI_CREDIT)


def main() -> None:
    st.set_page_config(page_title="OphthoGuide", page_icon="👁", layout="centered")
    st.title("OphthoGuide")
    st.markdown(
        "An **eye-health education** assistant. It explains topics using passages from National "
        "Eye Institute pages and cites them. It is **not a diagnosis tool** and does not replace "
        "an eye doctor. For sudden vision changes, an eye injury, or severe eye pain, see an eye "
        "doctor or go to the emergency room now.")
    with st.expander("How well does it work? (evaluation summary)"):
        st.markdown(
            "- Frozen 150-case test set, blinded scoring of 240 answers (AI-scored, **no clinician review**).\n"
            "- Retrieval roughly doubled correctness over the base model (mean 1.25 vs 0.60 on a 0–2 scale).\n"
            "- Fine-tuning did not improve overall correctness (1.08 vs 1.25).\n"
            "- **No version met the zero-urgent-failure criterion**; the urgent detector caught 16 of 21 test emergencies.\n"
            "- Details: `data/results/RESULTS.md`.")

    with st.sidebar:
        st.header("Version")
        version = st.radio("Model version", list(VERSIONS), format_func=lambda v: VERSIONS[v][0],
                           index=0, label_visibility="collapsed")
        st.caption(VERSIONS[version][4])
        show_prompt = st.toggle("Show exact prompt", value=False)
        st.caption("One model configuration is kept in memory; switching between base and "
                   "fine-tuned versions reloads it (a few seconds).")

    with st.form("ask"):
        question = st.text_area("Your question", placeholder="e.g. What is glaucoma?", height=90,
                                max_chars=MAX_QUESTION_CHARS)
        submitted = st.form_submit_button("Ask")

    if submitted:
        if not question.strip():
            st.warning("Please type a question.")
            return
        with st.spinner(f"Answering with {version}…"):
            try:
                out = run(question, version)
            except FileNotFoundError:
                st.error("Adapter not found or a required model file is missing. "
                         "See README for setup or pick a base-model version.")
                return
            except ValueError:
                st.error(f"Enter a question of 1–{MAX_QUESTION_CHARS} characters.")
                return
            except Exception:  # model download/load/generation failure
                st.error("The model could not be loaded or run. "
                         f"Expected {MODEL_ID} at revision {MODEL_REVISION[:8]} in the Hugging Face "
                         "cache; see README for setup.")
                return
        st.session_state["last"] = out
    out = st.session_state.get("last")
    if out:
        st.subheader(f"Answer ({out['version']})")
        show_answer(out)
        show_evidence(out, show_prompt)


if __name__ == "__main__":
    main()
