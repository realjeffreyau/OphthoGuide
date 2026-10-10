"""Multi-turn chat evaluation (separate from the frozen single-turn test set).

Runs every conversation in data/evaluation_chat/chat_cases.jsonl through chat.respond()
with one version, and writes the full transcripts. `--report` prints automatic checks:

  context   expected reported facts present in the patient context after the last turn
  urgent    urgent notice from the expected turn on (and not before it, for non-urgent turns)
  must_not  forbidden phrases absent from the final answer (case-insensitive)
  cites     invalid citations (IDs not supplied)
  questions more than 2 questions in one reply; a question repeated from an earlier reply
  time      seconds per turn

These are heuristics; the reviewed scores are in data/evaluation_chat/RESULTS.md.

  .venv/bin/python scripts/run_chat_eval.py --version B*
  .venv/bin/python scripts/run_chat_eval.py --report B* D*
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CASES = ROOT / "data/evaluation_chat/chat_cases.jsonl"
OUT = ROOT / "data/evaluation_chat"
ADAPTER = ROOT / "adapters/selected"


def tag(v: str) -> str:
    return v.replace("*", "star")


def run(version: str, cases_file: Path, prefix: str) -> None:
    import chat
    out = OUT / f"{prefix}_{tag(version)}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    with out.open("a", encoding="utf-8") as f:
        for case in map(json.loads, cases_file.read_text(encoding="utf-8").splitlines()):
            if case["id"] in done:
                continue
            msgs, ctx, turns = [], chat.PatientContext(), []
            for text in case["turns"]:
                r = chat.respond(text, msgs, ctx, version, str(ADAPTER), conv_id=case["id"])
                msgs += [{"role": "user", "content": text, "topic_start": r["topic_changed"]}, r]
                turns.append({"user": text, "answer": r["content"], "raw": r["raw"], "urgent": r["urgent"],
                              "query": r["query"], "topic_changed": r["topic_changed"], "weak": r["weak"],
                              "supplied": [x["chunk_id"] for x in r["results"]],
                              "cited": r["citations"]["cited"], "invalid": r["citations"]["invalid"],
                              "removed": [c["claim"] for c in r["removed"]], "restored": r["restored"],
                              "seconds": r["seconds"], "context": ctx.lines()})
                print(f"{version} {case['id']} turn {len(turns)}: {r['seconds']}s", flush=True)
            f.write(json.dumps({"id": case["id"], "version": version, "turns": turns}, ensure_ascii=False) + "\n")
            f.flush()


QUESTION = re.compile(r"[^.?!\n]*\?")


def report(versions: list[str], cases_file: Path, prefix: str) -> None:
    cases = {c["id"]: c for c in map(json.loads, cases_file.read_text(encoding="utf-8").splitlines())}
    for v in versions:
        runs = [json.loads(l) for l in (OUT / f"{prefix}_{tag(v)}.jsonl").read_text(encoding="utf-8").splitlines()]
        ctx_ok = urgent_ok = must_ok = 0
        inv = many_q = repeat_q = removed = 0
        secs, problems = [], []
        for run in runs:
            exp = cases[run["id"]]["expect"]
            last = run["turns"][-1]
            have = " | ".join(last["context"])
            miss = [x for x in exp["facts"] if x not in have]
            ctx_ok += not miss
            u_from = exp["urgent_from_turn"]
            flags = [t["urgent"] for t in run["turns"]]
            want = [bool(u_from) and i + 1 >= u_from for i in range(len(flags))]
            urgent_ok += flags == want
            final = last["answer"].lower()
            bad = [p for p in exp["must_not"] if p.lower() in final]
            must_ok += not bad
            asked: list[str] = []
            for t in run["turns"]:
                inv += bool(t["invalid"])
                removed += len(t["removed"])
                secs.append(t["seconds"])
                qs = [q.strip().lower() for q in QUESTION.findall(t["answer"])]
                many_q += len(qs) > 2
                repeat_q += any(q in asked for q in qs)
                asked += qs
            if miss or bad or flags != want:
                problems.append(f"{run['id']}:" + (f" missing facts {miss}" if miss else "")
                                + (f" forbidden {bad}" if bad else "")
                                + (f" urgent {flags} want {want}" if flags != want else ""))
        n = len(runs)
        print(f"== {v}: {n} conversations, {len(secs)} turns")
        print(f"  context facts correct   {ctx_ok}/{n}")
        print(f"  urgency flags correct   {urgent_ok}/{n}")
        print(f"  no forbidden phrases    {must_ok}/{n}")
        print(f"  turns w/ invalid cites  {inv}")
        print(f"  replies with >2 qs      {many_q}   repeated questions {repeat_q}")
        print(f"  verifier removals       {removed}")
        print(f"  seconds/turn            median {statistics.median(secs):.1f}  max {max(secs):.1f}")
        for p in problems:
            print("   -", p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", choices=["B*", "D*", "B", "D", "A", "C"])
    ap.add_argument("--report", nargs="*")
    ap.add_argument("--set", choices=["dev", "heldout"], default="dev",
                    help="dev = chat_cases.jsonl (used while tuning); heldout = chat_heldout.jsonl")
    args = ap.parse_args()
    cases_file = CASES if args.set == "dev" else OUT / "chat_heldout.jsonl"
    prefix = "runs" if args.set == "dev" else "heldout"
    if args.report:
        report(args.report, cases_file, prefix)
    elif args.version:
        run(args.version, cases_file, prefix)
    else:
        ap.error("--version or --report")
    return 0


if __name__ == "__main__":
    sys.exit(main())
