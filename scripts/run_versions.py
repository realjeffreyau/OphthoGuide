"""Run one evaluation version of OphthoGuide over a case set and log every answer.

Versions (same system prompt, sampler, output limit and per-case seed in all of them):
  A   base model,   no retrieval    raw model output
  B   base model,   retrieval       raw model output
  C   adapter,      no retrieval    raw model output
  D   adapter,      retrieval       raw model output
  B*  base model,   retrieval       full v10 pipeline (verifier, urgent notice, caveats)
  D*  adapter,      retrieval       full v10 pipeline; the verifier also runs on the adapted model

"Raw" means the model's own text with only the empty think block removed, so the
comparison measures the model and retrieval, not the code safeguards.

Case sets: the frozen test set (data/evaluation/test_cases.jsonl) or the validation
questions (data/training/valid.jsonl + review_notes.jsonl). Only one model configuration
is loaded per process. The output is resumable: finished case ids are skipped.

  .venv/bin/python scripts/run_versions.py --version B --set valid
  .venv/bin/python scripts/run_versions.py --version D --set test --adapter adapters/selected
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import assistant  # noqa: E402
from assistant import (CITE_BRACKET, CITE_ID, MAX_TOKENS, MODEL_ID, SYSTEM_PROMPT,  # noqa: E402
                       TEMPERATURE, URGENT_NOTICE, build_user_message, generate_answer,
                       retrieve_evidence)

MODEL_REVISION = "52a5ab34fa604bc8af6d3ce0cac0cab10b7eb495"
TOP_P = 0.9
VERSIONS = {  # name: (uses adapter, uses retrieval, full pipeline)
    "A": (False, False, False), "B": (False, True, False),
    "C": (True, False, False), "D": (True, True, False),
    "B*": (False, True, True), "D*": (True, True, True),
}
TEST_FILE = ROOT / "data/evaluation/test_cases.jsonl"
VALID_FILE = ROOT / "data/training/valid.jsonl"
NOTES_FILE = ROOT / "data/training/review_notes.jsonl"
FROZEN = ROOT / "data/results/FROZEN_CONFIG.json"
# Everything that can change a test answer. Hashed at the freeze; test runs refuse to start
# if any of it differs, so the test set is only ever run with the configuration chosen on
# validation data.
FROZEN_FILES = ["scripts/assistant.py", "scripts/retrieval.py", "scripts/run_versions.py",
                "data/processed/chunks.jsonl", "data/evaluation/test_cases.jsonl",
                "adapters/selected/adapters.safetensors", "adapters/selected/adapter_config.json"]


def file_hashes() -> dict[str, str]:
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FROZEN_FILES}


def freeze() -> None:
    import datetime
    FROZEN.write_text(json.dumps({
        "frozen": datetime.date.today().isoformat(),
        "settings": {"model": MODEL_ID, "revision": MODEL_REVISION, "temp": TEMPERATURE,
                     "top_p": TOP_P, "max_tokens": MAX_TOKENS, "seed": "sha256(case_id)[:8]",
                     "adapter": "adapters/selected (run_01 checkpoint 200)"},
        "sha256": file_hashes()}, indent=1), encoding="utf-8")
    print(f"froze {len(FROZEN_FILES)} files -> {FROZEN}")


def check_frozen() -> None:
    if not FROZEN.exists():
        sys.exit("no FROZEN_CONFIG.json: run --freeze after finishing validation")
    want = json.loads(FROZEN.read_text(encoding="utf-8"))["sha256"]
    changed = [f for f, h in file_hashes().items() if want.get(f) != h]
    if changed:
        sys.exit("configuration changed since the freeze: " + ", ".join(changed)
                 + "\nTest results would be exploratory. Refusing to run.")


def load_cases(which: str) -> list[dict]:
    if which == "test":
        return [{"case_id": c["id"], "question": c["question"], "category": c["category"],
                 "expected_action": c["expected_action"]}
                for c in map(json.loads, TEST_FILE.read_text(encoding="utf-8").splitlines())]
    notes = [n for n in map(json.loads, NOTES_FILE.read_text(encoding="utf-8").splitlines())
             if n["split"] == "valid"]
    rows = [json.loads(l) for l in VALID_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(notes) == len(rows), "review_notes and valid.jsonl are out of step"
    out = []
    for n, r in zip(notes, rows):
        q = r["messages"][1]["content"].split("Question:\n", 1)[1].strip()
        assert q == n["question"].strip(), n["id"]
        out.append({"case_id": n["id"], "question": q, "category": n["behaviour"]})
    return out


def case_seed(case_id: str) -> int:
    return int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16)


def cited_ids(text: str) -> list[str]:
    return list(dict.fromkeys(c for g in CITE_BRACKET.findall(text or "") for c in CITE_ID.findall(g)))


def run_case(case: dict, version: str, adapter: str | None) -> dict:
    _, use_retrieval, full = VERSIONS[version]
    seed = case_seed(case["case_id"])
    t0 = time.perf_counter()
    if full:
        rec = assistant.answer(case["question"], retrieval=True, seed=seed)
        results, weak, user = rec["results"], rec["weak_evidence"], rec["prompt"]
        text = rec["answer"]
        if rec["urgent"]:
            text = URGENT_NOTICE + "\n\n" + text
        extra = {"caveats": [c["text"] for c in rec.get("caveats") or []],
                 "removed_claims": [c["claim"] for c in (rec.get("verification") or {}).get("removed", [])],
                 "urgent_notice": rec["urgent"]}
    else:
        results, weak = retrieve_evidence(case["question"]) if use_retrieval else ([], False)
        user = build_user_message(case["question"], results, weak, use_retrieval)
        text = generate_answer(SYSTEM_PROMPT, user, seed=seed)
        extra = {}
    elapsed = time.perf_counter() - t0
    supplied = [] if weak else [r["chunk_id"] for r in results]
    return {
        "case_id": case["case_id"], "version": version, "category": case["category"],
        "expected_action": case.get("expected_action"), "question": case["question"],
        "answer": text,
        "retrieved_chunk_ids": [r["chunk_id"] for r in results],
        "supplied_chunk_ids": supplied, "weak_evidence": weak,
        "cited_chunk_ids": cited_ids(text),
        "generation_settings": {"model": MODEL_ID, "revision": MODEL_REVISION, "adapter": adapter,
                                "retrieval": use_retrieval, "pipeline": "v10" if full else "raw",
                                "temp": TEMPERATURE, "top_p": TOP_P, "max_tokens": MAX_TOKENS,
                                "seed": seed},
        "response_time_seconds": round(elapsed, 2),
        "prompt_sha": hashlib.sha256((SYSTEM_PROMPT + "\x00" + user).encode()).hexdigest()[:16],
        **extra,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true", help="record hashes of the final configuration")
    ap.add_argument("--version", choices=list(VERSIONS))
    ap.add_argument("--set", choices=["valid", "test"])
    ap.add_argument("--adapter", default="adapters/selected")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    if args.freeze:
        freeze()
        return 0
    if not (args.version and args.set):
        ap.error("--version and --set are required")
    if args.set == "test":
        check_frozen()

    uses_adapter = VERSIONS[args.version][0]
    adapter = args.adapter if uses_adapter else None
    if adapter and not (ROOT / adapter / "adapters.safetensors").exists():
        sys.exit(f"adapter not found: {adapter}/adapters.safetensors")
    assistant.configure(str(ROOT / adapter) if adapter else None)

    tag = args.version.replace("*", "star")
    out = args.out or ROOT / f"data/results/{args.set}_{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["case_id"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    cases = [c for c in load_cases(args.set) if c["case_id"] not in done][: args.limit]
    print(f"{args.version} on {args.set}: {len(cases)} to run, {len(done)} already done -> {out}",
          flush=True)
    with out.open("a", encoding="utf-8") as f:
        for n, case in enumerate(cases, 1):
            rec = run_case(case, args.version, adapter)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{n}/{len(cases)}] {case['case_id']} {rec['response_time_seconds']}s "
                  f"cites={len(rec['cited_chunk_ids'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
