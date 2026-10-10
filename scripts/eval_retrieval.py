"""Evaluate BM25 retrieval against hand-labelled questions.

Usage:
    .venv/bin/python scripts/eval_retrieval.py [--questions FILE] [--out CSV] [-k 4]
                                               [--no-expand] [--show-misses]

Each question lists evidence quotes chosen by hand ({doc_id, quote}). Expected chunk IDs
are every chunk of that document containing the quote, so labels survive re-chunking.
A quote that no longer matches any chunk is an error (the corpus changed: re-check it).

A question with no evidence is out of corpus. It counts as correct when retrieval flags
weak evidence (see retrieval.WEAK_COVERAGE) instead of returning confident passages.

Writes: question_id, expected_chunk_ids, retrieved_chunk_ids, relevant_hit,
        top_coverage, weak_evidence
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from retrieval import build_index, is_weak, normalize, retrieve

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "eval" / "retrieval_questions.jsonl"
RESULTS = ROOT / "data" / "eval" / "retrieval_results.csv"


def expected_ids(q: dict, chunks: list[dict]) -> list[str]:
    ids = []
    for ev in q["evidence"]:
        quote = normalize(ev["quote"])
        found = [c["chunk_id"] for c in chunks
                 if c["doc_id"] == ev["doc_id"] and quote in normalize(c["text"])]
        if not found:
            raise ValueError(f"{q['question_id']}: quote not found in {ev['doc_id']}: {ev['quote']!r}")
        ids += [i for i in found if i not in ids]
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("--questions", type=Path, default=QUESTIONS)
    ap.add_argument("--out", type=Path, default=RESULTS)
    ap.add_argument("--no-expand", action="store_true", help="disable lay-term query expansion")
    ap.add_argument("--show-misses", action="store_true", help="print top passages for misses")
    args = ap.parse_args()

    questions = [json.loads(l) for l in args.questions.read_text(encoding="utf-8").splitlines() if l.strip()]
    index = build_index()
    rows, hits, rr_total, answerable = [], 0, 0.0, 0
    ooc_total = ooc_ok = false_weak = 0
    for q in questions:
        try:
            expected = expected_ids(q, index.chunks)
        except ValueError as e:
            print(f"ERROR {e}", file=sys.stderr)
            return 2
        results = retrieve(q["question"], k=args.k, index=index, expand=not args.no_expand)
        got = [r["chunk_id"] for r in results]
        weak = is_weak(results)
        top_cov = results[0]["coverage"] if results else 0.0

        if expected:
            answerable += 1
            first = next((i for i, c in enumerate(got, 1) if c in expected), None)
            hit = first is not None
            hits += hit
            rr_total += 1 / first if first else 0
            false_weak += weak
            mark = f"HIT@{first}" if hit else "MISS"
        else:
            ooc_total += 1
            hit = weak
            ooc_ok += weak
            mark = "OOC-OK" if weak else "OOC-BAD"
        rows.append({
            "question_id": q["question_id"],
            "expected_chunk_ids": ";".join(expected),
            "retrieved_chunk_ids": ";".join(got),
            "relevant_hit": hit,
            "top_coverage": round(top_cov, 2),
            "weak_evidence": weak,
        })
        flag = "  [weak evidence]" if weak and expected else ""
        print(f"{q['question_id']} {mark:7s} cov={top_cov:.2f} {q['question']}{flag}")
        if args.show_misses and (not hit or (weak and expected)):
            for r in results:
                print(f"        #{r['rank']} {r['chunk_id']} score={r['score']:.2f} "
                      f"cov={r['coverage']:.2f} [{r['title']} > {r['section']}]")

    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    if answerable:
        print(f"\nanswerable hit@{args.k}: {hits}/{answerable} = {hits / answerable:.0%}   "
              f"MRR@{args.k}: {rr_total / answerable:.3f}   wrongly flagged weak: {false_weak}")
    if ooc_total:
        print(f"out-of-corpus correctly flagged weak: {ooc_ok}/{ooc_total}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
