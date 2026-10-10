"""Build the expanded chat corpus (72 NEI pages) next to the frozen 50-page evaluation corpus.

The single-turn evaluation pins data/processed/chunks.jsonl and scripts/retrieval.py by hash,
so the chat uses its own files and the unchanged chunking code:

  .venv/bin/python scripts/collect_sources.py --sources data/sources/nei_pages_chat.csv \
      --out data/processed_chat/documents.jsonl
  .venv/bin/python scripts/validate_documents.py data/processed_chat/documents.jsonl
  .venv/bin/python scripts/build_chat_corpus.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from retrieval import load_documents, make_chunks, save_chunks  # noqa: E402

DOCS = ROOT / "data/processed_chat/documents.jsonl"
CHUNKS = ROOT / "data/processed_chat/chunks.jsonl"


def main() -> int:
    docs = load_documents(DOCS)
    chunks = make_chunks(docs)
    save_chunks(chunks, CHUNKS)
    sizes = sorted(c["word_count"] for c in chunks)
    print(f"{len(docs)} docs -> {len(chunks)} chunks ({sizes[0]}–{sizes[-1]} words) -> "
          f"{CHUNKS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
