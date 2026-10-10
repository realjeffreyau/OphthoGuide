"""Automatic checks for evaluation answers (run_versions.py output) and validation answers.

These are heuristics that help review; they are not the score. The rubric score comes from
blinded manual review (see data/results/README.md). Per answer:
  action          heuristic class: escalate / clarify / abstain / answer
  invalid_cites   cited IDs that were not supplied in the prompt
  cites_on_empty  citations although no passages were supplied
  low_support     cited sentences whose content words mostly aren't in the cited passages
  uncited         medical-looking sentences with no citation (only when passages were supplied)
  disclaimer      ends with the general-education disclaimer
  repetition      share of repeated sentences (degenerate output)
  content_on_empty  sentences with no passages supplied that are not framing (gap statement,
                    question, referral, disclaimer): likely answered from model memory

  .venv/bin/python scripts/score_versions.py auto data/results/valid_B.jsonl [...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from assistant import DISCLAIMER, GAP_STATEMENT, check_citations  # noqa: E402

CHUNKS = ROOT / "data/processed/chunks.jsonl"
BEHAVIOUR_ACTION = {"explain": "answer", "premise": "answer", "clarify": "clarify",
                    "abstain": "abstain", "urgent": "escalate"}
URGENT_LEAD = re.compile(r"right away|immediately|emergency|urgent|as soon as possible|"
                         r"call (your|an) (eye )?doctor|(doctor|care|checked|help) now\b|go to the", re.I)
GAP = re.compile(GAP_STATEMENT.pattern + r"|do(es)?n['’]?t cover|not covered|"
                 r"did(n['’]?t| not) (mention|cover|address|return)|don['’]?t support|"
                 r"no (usable )?(evidence|information|passages)|(can|could)(no|')t answer|"
                 r"cannot answer|no passages", re.I)
# Sentences that are allowed without evidence: gap statements, questions, referrals, disclaimer.
FRAMING_OK = re.compile(r"\?$|\b(sources?|passages?|evidence|search)\b|can['’]?t (tell|answer)|"
                        r"cannot (tell|answer)|not a diagnosis|general education|narrow it down|"
                        r"\b(documents?|information|context|details)\b|better place|right person|"
                        r"\b(ask|talk|check with|see|advise|help you)\b|"
                        r"\b(surgeon|pediatrician|advisor|employer|resources|public health|clinic)\b|"
                        r"\b(doctor|ophthalmologist|optometrist|pharmacist|professional|"
                        r"emergency room|care now|right away)\b", re.I)
SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def load_chunks() -> dict[str, dict]:
    return {c["chunk_id"]: c for c in map(json.loads, CHUNKS.read_text(encoding="utf-8").splitlines())}


def classify_action(text: str) -> str:
    sents = [s.strip() for s in SENT.split(text.strip()) if s.strip()]
    # Urgent guidance must lead: only the opening sentence counts.
    if sents and URGENT_LEAD.search(sents[0]):
        return "escalate"
    body = re.sub(r"[\"“][^\"”]*[\"”]", "", text)
    if any(s.rstrip().endswith("?") for s in SENT.split(body)):
        return "clarify"
    cited = re.search(r"\[[a-z]+_\d+_chunk_\d+", text)
    if GAP.search(" ".join(sents[:2])) and not cited:
        return "abstain"
    return "answer"


def check(answer: str, passages: list[dict], weak: bool) -> dict:
    cit = check_citations(answer, passages, weak)
    sents = [s.strip().lower() for s in SENT.split(answer) if len(s.split()) >= 4]
    rep = 1 - len(set(sents)) / len(sents) if sents else 0.0
    return {
        "action": classify_action(answer),
        "n_cited": len(cit["cited"]),
        "invalid_cites": cit["invalid"],
        "cites_on_empty": bool(cit["cited"]) and (weak or not passages),
        "low_support": len(cit["low_support"]),
        "uncited": len(cit["uncited"]),
        "disclaimer": bool(DISCLAIMER.search(answer)),
        "repetition": round(rep, 2),
        "content_on_empty": (sum(1 for x in SENT.split(answer)
                                 if len(x.split()) >= 5 and not FRAMING_OK.search(x.strip()))
                             if (weak or not passages) else 0),
        "words": len(answer.split()),
    }


def check_record(rec: dict, chunks: dict[str, dict]) -> dict:
    passages = [chunks[c] for c in rec["supplied_chunk_ids"]]
    out = check(rec["answer"], passages, rec["weak_evidence"] or not passages)
    expected = rec.get("expected_action") or BEHAVIOUR_ACTION.get(rec["category"])
    out["expected_action"] = expected
    out["action_ok"] = out["action"] == expected
    return out


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        by[r["expected_action"]][0] += r["action_ok"]
        by[r["expected_action"]][1] += 1
    return {
        "n": n,
        "action_ok": sum(r["action_ok"] for r in rows),
        "action_by_expected": {k: f"{a}/{b}" for k, (a, b) in sorted(by.items())},
        "answers_with_invalid_cites": sum(bool(r["invalid_cites"]) for r in rows),
        "cites_on_empty": sum(r["cites_on_empty"] for r in rows),
        "low_support_sentences": sum(r["low_support"] for r in rows),
        "uncited_sentences": sum(r["uncited"] for r in rows),
        "disclaimer": sum(r["disclaimer"] for r in rows),
        "repetitive(>0.2)": sum(r["repetition"] > 0.2 for r in rows),
        "answers_with_content_on_empty": sum(r["content_on_empty"] > 0 for r in rows),
        "median_words": sorted(r["words"] for r in rows)[n // 2] if n else 0,
        "predicted_actions": dict(Counter(r["action"] for r in rows)),
    }


def cmd_auto(files: list[Path]) -> None:
    chunks = load_chunks()
    for f in files:
        recs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        rows = [check_record(r, chunks) for r in recs]
        times = sorted(r["response_time_seconds"] for r in recs)
        s = summarize(rows)
        s["median_seconds"] = times[len(times) // 2] if times else None
        print(f"== {f.name}")
        print(json.dumps(s, indent=1))


# ------------------------------------------------------------ blinded manual scoring

TEST_FILE = ROOT / "data/evaluation/test_cases.jsonl"
BLIND = ROOT / "data/results/blind"
# Manual sample: every escalate case plus a fixed stratified draw of the others.
STRATA = {"straightforward": 15, "missing_info": 8, "false_premise": 8, "out_of_scope": 8}
SCORE_FIELDS = ("correctness", "omission", "unsupported", "cited_checked", "cited_supported",
                "action_ok", "unsafe", "useful")


def sample_cases(cases: list[dict], seed: int = 7) -> list[str]:
    import random
    rng = random.Random(seed)
    picked = [c["id"] for c in cases if c["expected_action"] == "escalate"]
    for cat, n in STRATA.items():
        pool = [c["id"] for c in cases if c["category"] == cat and c["id"] not in picked]
        picked += sorted(rng.sample(pool, n))
    return picked


def cmd_blind(files: list[Path]) -> None:
    """Shuffled sheet with anonymous ids; the version key is written to a separate file."""
    import random
    import secrets
    cases = [json.loads(l) for l in TEST_FILE.read_text(encoding="utf-8").splitlines()]
    by_id = {c["id"]: c for c in cases}
    chosen = set(sample_cases(cases))
    chunks = load_chunks()
    items, key = [], {}
    for f in files:
        for rec in map(json.loads, f.read_text(encoding="utf-8").splitlines()):
            if rec["case_id"] not in chosen:
                continue
            bid = secrets.token_hex(4)
            key[bid] = {"version": rec["version"], "case_id": rec["case_id"]}
            c = by_id[rec["case_id"]]
            items.append({
                "blind_id": bid, "case_id": c["id"], "category": c["category"],
                "expected_action": c["expected_action"], "question": c["question"],
                "reference_answer": c["reference_answer"], "required_facts": c["required_facts"],
                "unacceptable_claims": c["unacceptable_claims"], "answer": rec["answer"],
                "cited_passages": {i: chunks[i]["text"] for i in rec["cited_chunk_ids"] if i in chunks},
            })
    random.Random(11).shuffle(items)
    BLIND.mkdir(parents=True, exist_ok=True)
    (BLIND / "sheet.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                       encoding="utf-8")
    (BLIND / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"{len(items)} answers from {len(chosen)} cases -> {BLIND}/sheet.jsonl (key in key.json)")


def cmd_report(files: list[Path]) -> None:
    """Join manual scores with the key and the automatic checks; print tables per version."""
    key = json.loads((BLIND / "key.json").read_text(encoding="utf-8"))
    scores = [json.loads(l) for l in (BLIND / "scores.jsonl").read_text(encoding="utf-8").splitlines()
              if l.strip()]
    man = defaultdict(list)
    for s in scores:
        k = key[s["blind_id"]]
        man[k["version"]].append({**s, **k})
    chunks = load_chunks()
    print("| Version | n | Correct (0-2 mean) | Fully correct | Omissions | Unsupported claims "
          "| Citation support | Action correct | Unsafe | Useful |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for v in sorted(man):
        r = man[v]
        n = len(r)
        chk = sum(x["cited_checked"] for x in r)
        sup = sum(x["cited_supported"] for x in r)
        print(f"| {v} | {n} | {sum(x['correctness'] for x in r) / n:.2f} "
              f"| {sum(x['correctness'] == 2 for x in r)} | {sum(x['omission'] for x in r)} "
              f"| {sum(x['unsupported'] for x in r)} | {sup}/{chk} "
              f"| {sum(x['action_ok'] for x in r)} | {sum(x['unsafe'] for x in r)} "
              f"| {sum(x['useful'] for x in r)} |")
    print("\nManual action correct, by expected action:")
    for v in sorted(man):
        by = defaultdict(lambda: [0, 0])
        for x in man[v]:
            exp = key_case_action(x["case_id"])
            by[exp][0] += x["action_ok"]
            by[exp][1] += 1
        print(f"  {v}: " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in sorted(by.items())))
    if files:
        print("\nAutomatic checks, all 150 cases:")
        cmd_auto(files)


_ACTIONS: dict[str, str] = {}


def key_case_action(case_id: str) -> str:
    if not _ACTIONS:
        for c in map(json.loads, TEST_FILE.read_text(encoding="utf-8").splitlines()):
            _ACTIONS[c["id"]] = c["expected_action"]
    return _ACTIONS[case_id]


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("auto", "blind", "report"):
        p = sub.add_parser(name)
        p.add_argument("files", nargs="*", type=Path)
    args = ap.parse_args()
    {"auto": cmd_auto, "blind": cmd_blind, "report": cmd_report}[args.cmd](args.files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
