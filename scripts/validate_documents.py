"""Validate data/processed/documents.jsonl.

Usage: .venv/bin/python scripts/validate_documents.py
Exit code 0 = all checks pass.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "processed" / "documents.jsonl"
if len(__import__("sys").argv) > 1:  # optional path, e.g. data/processed_chat/documents.jsonl
    DOCS = Path(__import__("sys").argv[1]).resolve()

REQUIRED = ["id", "title", "url", "updated", "retrieved", "topic", "reuse", "text"]
REUSE_OK = {"public_domain_verified"}
MIN_WORDS = 150  # anatomy pages (e.g. "How the Eyes Work") are short by design
NAV_RESIDUE = ["Skip to content", "Was this page helpful", "Back to top",
               "NIH Websites Are Changing", "Learn more about", "Print this page"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main() -> int:
    errors, warnings, docs = [], [], []
    for n, line in enumerate(DOCS.read_text(encoding="utf-8").splitlines(), 1):
        try:
            docs.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"line {n}: invalid JSON ({e})")

    ids = Counter(d.get("id") for d in docs)
    errors += [f"duplicate id {i}" for i, c in ids.items() if c > 1]

    for d in docs:
        did = d.get("id", "?")
        missing = [k for k in REQUIRED if k not in d]
        if missing:
            errors.append(f"{did}: missing fields {missing}")
            continue
        if not d["title"]:
            errors.append(f"{did}: empty title")
        if not d["url"].startswith("https://www.nei.nih.gov/"):
            errors.append(f"{did}: unexpected url {d['url']}")
        if d["updated"] is not None and not DATE_RE.match(d["updated"]):
            errors.append(f"{did}: bad updated date {d['updated']!r}")
        if d["updated"] is None:
            warnings.append(f"{did}: no update date")
        if not DATE_RE.match(d["retrieved"]):
            errors.append(f"{did}: bad retrieved date {d['retrieved']!r}")
        if d["reuse"] not in REUSE_OK:
            errors.append(f"{did}: reuse={d['reuse']} (see collection_report.md)")
        words = len(d["text"].split())
        if words < MIN_WORDS:
            errors.append(f"{did}: only {words} words")
        for r in NAV_RESIDUE:
            if r in d["text"]:
                errors.append(f"{did}: nav residue {r!r}")
        heads = sum(1 for ln in d["text"].splitlines() if ln.startswith("#"))
        if heads == 0 and words > 400:
            warnings.append(f"{did}: long text with no headings")

    topics = Counter(d.get("topic") for d in docs)
    print(f"{len(docs)} documents, {sum(len(d['text'].split()) for d in docs)} words")
    for t, c in sorted(topics.items()):
        print(f"  {t:22s} {c}")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("PASS" if not errors else f"FAIL ({len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
