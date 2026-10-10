"""Build, validate, and freeze the OphthoGuide evaluation set.

Usage:
    .venv/bin/python scripts/build_test_cases.py              # build + validate; refuses to change a frozen set
    .venv/bin/python scripts/build_test_cases.py --refreeze   # deliberately replace the frozen set (bumps version)
    .venv/bin/python scripts/build_test_cases.py --verify     # check test_cases.jsonl still matches MANIFEST.json
    .venv/bin/python scripts/build_test_cases.py --check-train FILE.jsonl
        # leakage check for future training data: flags any record whose text overlaps a test question
        # or reference answer (exact or near-duplicate). Exit 1 if anything overlaps.

Sources: data/evaluation/src/cases_*.py (hand-written; every required fact carries a verbatim
quote from data/processed/documents.jsonl). Output: data/evaluation/test_cases.jsonl and MANIFEST.json.
The evaluation files must never be indexed for retrieval or used for training.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import runpy
import sys
from collections import Counter
from pathlib import Path

from retrieval import CHUNKS_PATH, DOCS_PATH, normalize, tokenize

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "data" / "evaluation"
SRC_FILES = ["cases_straightforward.py", "cases_missing_info.py", "cases_other.py"]
OUT = EVAL_DIR / "test_cases.jsonl"
MANIFEST = EVAL_DIR / "MANIFEST.json"
SOURCES_CSV = ROOT / "data" / "sources" / "nei_pages.csv"
TUNING_QUESTION_FILES = sorted((ROOT / "data" / "eval").glob("*questions*.jsonl")) + \
    sorted((ROOT / "data" / "eval").glob("retrieval_*.jsonl"))

CATEGORY_COUNTS = {"straightforward": 60, "missing_info": 30, "urgent": 20,
                   "false_premise": 20, "out_of_scope": 20}
ALLOWED_ACTIONS = {
    "straightforward": {"answer"},
    "missing_info": {"clarify", "answer"},
    "urgent": {"escalate"},
    "false_premise": {"answer", "abstain", "escalate"},
    "out_of_scope": {"abstain"},
}
DEFAULT_ACTION = {"straightforward": "answer", "missing_info": "clarify", "urgent": "escalate",
                  "false_premise": "answer", "out_of_scope": "abstain"}
NEAR_DUP_JACCARD = 0.6


def _plain(s: str) -> str:
    s = normalize(s).lower()
    s = re.sub(r"(^|\s)[-•#]+\s+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _jaccard(a: str, b: str) -> float:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_sources() -> list[dict]:
    raw = []
    for name in SRC_FILES:
        mod = runpy.run_path(str(EVAL_DIR / "src" / name))
        default_cat = mod.get("CATEGORY")
        for c in mod["CASES"]:
            raw.append({**c, "category": c.get("category", default_cat)})
    order = list(CATEGORY_COUNTS)
    raw.sort(key=lambda c: order.index(c["category"]))  # stable: keeps authoring order within category
    return raw


def build(raw: list[dict]) -> list[dict]:
    cases = []
    for i, c in enumerate(raw, 1):
        cid = f"tc_{i:03d}"
        facts = c.get("facts", [])
        evidence = [{"fact": f, "doc_id": d, "quote": q} for f, d, q in facts]
        cited = re.findall(r"nei_\d{3}", c["reference_answer"])
        sources = list(dict.fromkeys([e["doc_id"] for e in evidence] + cited))
        case = {
            "id": cid,
            "category": c["category"],
            "question": c["question"],
            "reference_answer": c["reference_answer"],
            "required_facts": [f for f, _, _ in facts],
            "unacceptable_claims": c["unacceptable"],
            "expected_action": c.get("action", DEFAULT_ACTION[c["category"]]),
            "supporting_source_ids": sources,
            "evidence": evidence,
            "group_id": c.get("group") or f"g_{cid}",
            "split": "test",
            "review": {"clinical_review": "pending", "reviewer": None,
                       "priority": "high" if c["category"] in ("urgent", "missing_info") else "normal"},
        }
        if c.get("clarify"):
            case["clarifying_questions"] = c["clarify"]
        cases.append(case)
    return cases


def validate(cases: list[dict]) -> list[str]:
    errors = []
    docs = {d["id"]: d for d in map(json.loads, DOCS_PATH.read_text(encoding="utf-8").splitlines())}
    doc_plain = {k: _plain(f"{d['title']} {d['text']}") for k, d in docs.items()}

    counts = Counter(c["category"] for c in cases)
    if dict(counts) != CATEGORY_COUNTS:
        errors.append(f"category counts {dict(counts)} != required {CATEGORY_COUNTS}")
    if len({c["id"] for c in cases}) != len(cases):
        errors.append("duplicate ids")
    qs = Counter(_plain(c["question"]) for c in cases)
    errors += [f"duplicate question: {q}" for q, n in qs.items() if n > 1]

    required_fields = ["id", "category", "question", "reference_answer", "required_facts",
                       "unacceptable_claims", "expected_action", "supporting_source_ids"]
    for c in cases:
        cid = c["id"]
        for f in required_fields:
            if f not in c or c[f] in (None, ""):
                errors.append(f"{cid}: missing {f}")
        if c["expected_action"] not in ALLOWED_ACTIONS[c["category"]]:
            errors.append(f"{cid}: action {c['expected_action']} not allowed for {c['category']}")
        if not c["unacceptable_claims"]:
            errors.append(f"{cid}: no unacceptable claims")
        if c["expected_action"] != "abstain" and not c["required_facts"]:
            errors.append(f"{cid}: non-abstain case without required facts")
        if c["category"] == "missing_info" and c["expected_action"] == "clarify" and not c.get("clarifying_questions"):
            errors.append(f"{cid}: clarify case without clarifying_questions")
        for doc in c["supporting_source_ids"]:
            if doc not in docs:
                errors.append(f"{cid}: unknown source {doc}")
        for e in c["evidence"]:
            if e["doc_id"] not in docs:
                continue
            if _plain(e["quote"]) not in doc_plain[e["doc_id"]]:
                errors.append(f"{cid}: quote not found in {e['doc_id']}: {e['quote'][:70]!r}")
        if c["expected_action"] == "escalate":
            urgent_words = re.compile(r"right away|emergency|now|immediately|promptly", re.I)
            if not urgent_words.search(c["reference_answer"].split(".")[0]):
                errors.append(f"{cid}: escalate reference must lead with the urgent-care instruction")
            if not any(urgent_words.search(e["quote"]) for e in c["evidence"]):
                errors.append(f"{cid}: escalate case lacks source guidance quote containing urgency wording")

    groups = {}
    for c in cases:
        groups.setdefault(c["group_id"], []).append(c)
    for g, members in groups.items():
        if not g.startswith("g_tc_") and len(members) < 2:
            errors.append(f"paraphrase group {g} has only one member")
        if len({(m["category"], m["split"]) for m in members}) > 1:
            errors.append(f"paraphrase group {g} spans categories or splits")
    return errors


def tuning_overlap(cases: list[dict]) -> list[str]:
    tuning = []
    for f in TUNING_QUESTION_FILES:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tuning.append((f.name, json.loads(line)["question"]))
    out = []
    for c in cases:
        for fname, q in tuning:
            if _plain(q) == _plain(c["question"]) or _jaccard(q, c["question"]) >= NEAR_DUP_JACCARD:
                out.append(f"{c['id']} near-duplicates tuning question in {fname}: {q!r}")
    return out


def leakage(cases: list[dict]) -> list[str]:
    """The retrieval index must contain only NEI source documents — never test cases."""
    out = []
    allowed = {line.split(",")[0] for line in SOURCES_CSV.read_text(encoding="utf-8").splitlines()[1:] if line}
    doc_ids = {d["id"] for d in map(json.loads, DOCS_PATH.read_text(encoding="utf-8").splitlines())}
    if not doc_ids <= allowed:
        out.append(f"documents.jsonl has ids not in nei_pages.csv: {sorted(doc_ids - allowed)}")
    chunks = [json.loads(l) for l in CHUNKS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    if {c["doc_id"] for c in chunks} - doc_ids:
        out.append("chunks.jsonl contains doc_ids not in documents.jsonl")
    chunk_text = "\n".join(_plain(c["text"]) for c in chunks)
    for c in cases:
        # Questions may legitimately mirror NEI page headings ("What is glaucoma?"); the index is
        # built only from NEI documents (checked above), so check for test-set artifacts instead.
        if re.search(rf"\b{c['id']}\b", chunk_text):
            out.append(f"{c['id']}: test case id found in the retrieval index")
        # reference answers paraphrase sources; flag only if a whole reference sentence
        # that is NOT one of the case's evidence quotes appears verbatim in the index
        quotes = " ".join(_plain(e["quote"]) for e in c["evidence"])
        for sent in re.split(r"(?<=[.!?])\s+", c["reference_answer"]):
            s = _plain(re.sub(r"\(nei_\d{3}(, nei_\d{3})*\)", "", sent))
            if len(s.split()) >= 12 and s in chunk_text and s not in quotes:
                out.append(f"{c['id']}: reference sentence appears verbatim in index: {s[:60]!r}")
    retrieval_src = (ROOT / "scripts" / "retrieval.py").read_text(encoding="utf-8")
    if "_refuse_eval_path" not in retrieval_src:
        out.append("retrieval.py lacks the _refuse_eval_path guard against indexing data/evaluation")
    return out


def check_train(path: Path) -> int:
    """Flag training records whose *question* or *target answer* overlaps a test question or
    reference answer. Source evidence inside prompts is not checked: NEI pages are allowed to be
    searchable, and many test questions are NEI headings that naturally appear in passages."""
    cases = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()]
    hits = 0
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        if "messages" in rec:
            user = next((m["content"] for m in rec["messages"] if m["role"] == "user"), "")
            question = user.split("Question:\n")[-1]
            target = " ".join(m["content"] for m in rec["messages"] if m["role"] == "assistant")
        else:
            question = rec.get("question") or rec.get("prompt") or ""
            target = rec.get("answer") or rec.get("completion") or ""
        for c in cases:
            if _plain(question) == _plain(c["question"]) or _jaccard(question, c["question"]) >= NEAR_DUP_JACCARD:
                print(f"line {n}: question near-duplicates test case {c['id']} ({c['question'][:60]!r})")
                hits += 1
            ref = _plain(re.sub(r"\(nei_\d{3}(, nei_\d{3})*\)", "", c["reference_answer"]))
            if ref[:120] and ref[:120] in _plain(target):
                print(f"line {n}: target contains reference answer of {c['id']}")
                hits += 1
    print("leakage check:", "FAIL" if hits else "PASS", f"({hits} overlaps)")
    return 1 if hits else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refreeze", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--check-train", type=Path)
    args = ap.parse_args()

    if args.check_train:
        return check_train(args.check_train)
    if args.verify:
        m = json.loads(MANIFEST.read_text())
        ok = _sha256(OUT) == m["sha256"]
        print("test_cases.jsonl matches MANIFEST:", ok)
        return 0 if ok else 1

    cases = build(load_sources())
    problems = validate(cases) + tuning_overlap(cases) + leakage(cases)
    for p in problems:
        print("ERROR", p)
    counts = Counter(c["category"] for c in cases)
    actions = Counter(c["expected_action"] for c in cases)
    print(f"{len(cases)} cases | categories {dict(counts)} | actions {dict(actions)}")
    print(f"paraphrase groups: {sum(1 for g, n in Counter(c['group_id'] for c in cases).items() if n > 1)}")
    if problems:
        print(f"FAIL ({len(problems)} problems) — nothing written")
        return 1

    payload = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases)
    new_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else None
    if old and old.get("frozen") and old["sha256"] != new_hash and not args.refreeze:
        print("ERROR test set is frozen and the rebuilt content differs. Re-run with --refreeze only if the "
              "change is intended (e.g. after clinical review), and record why in data/evaluation/README.md.")
        return 1
    if old and old["sha256"] == new_hash:
        print(f"PASS — unchanged (sha256 {new_hash[:16]}…), still frozen")
        return 0

    OUT.write_text(payload, encoding="utf-8")
    version = (old["version"] + 1) if old else 1
    manifest = {
        "name": "OphthoGuide evaluation set",
        "version": version,
        "frozen": True,
        "frozen_on": dt.date.today().isoformat(),
        "sha256": new_hash,
        "n_cases": len(cases),
        "category_counts": dict(counts),
        "action_counts": dict(actions),
        "corpus_documents_sha256": _sha256(DOCS_PATH),
        "corpus_chunks_sha256": _sha256(CHUNKS_PATH),
        "clinical_review": "pending",
        "usage": "TEST ONLY. Never add to the retrieval index. Never use for training or prompt tuning.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"PASS — wrote {OUT.relative_to(ROOT)} (v{version}, sha256 {new_hash[:16]}…) and MANIFEST.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
