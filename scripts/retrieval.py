"""BM25 passage search over the OphthoGuide corpus.

Usage:
    .venv/bin/python scripts/retrieval.py --build          # write data/processed/chunks.jsonl
    .venv/bin/python scripts/retrieval.py "question" [-k 4]

BM25 scores are ranking scores: they say how well a passage's words match the
question relative to other passages. They are NOT probabilities that a passage
answers the question, and say nothing about medical correctness.
"""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_PATH = ROOT / "data" / "processed" / "documents.jsonl"
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"

MIN_WORDS = 150
MAX_WORDS = 250
OVERLAP_WORDS = 30
TAIL_MERGE_WORDS = 60  # a final chunk smaller than this joins the previous one


# ---------------------------------------------------------------- documents

EVAL_DIR = ROOT / "data" / "evaluation"


def _refuse_eval_path(path: Path) -> None:
    """The evaluation set (test cases, reference answers) must never enter the retrieval index."""
    if EVAL_DIR.resolve() in Path(path).resolve().parents:
        raise ValueError(f"refusing to index evaluation data: {path}")


def load_documents(path: Path = DOCS_PATH) -> list[dict]:
    _refuse_eval_path(path)
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ------------------------------------------------------------------ chunks

def _words(s: str) -> int:
    return len(s.split())


def _pieces(block: str) -> list[str]:
    """Split a block into sentence/list-item pieces (used for overlap and long blocks)."""
    if block.startswith("- "):
        return [p if p.startswith("- ") else "- " + p for p in block.split("\n- ")]
    return [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(])", block) if p]


def _split_long(block: str, max_words: int) -> list[str]:
    if _words(block) <= max_words:
        return [block]
    sep = "\n" if block.startswith("- ") else " "
    out, cur = [], []
    for p in _pieces(block):
        if cur and _words(sep.join(cur + [p])) > max_words:
            out.append(sep.join(cur))
            cur = []
        cur.append(p)
    if cur:
        out.append(sep.join(cur))
    return out


def _tail(units: list[dict], n_words: int) -> list[dict]:
    """Last ~n_words of the chunk as whole sentences/list items, newest last."""
    out, total = [], 0
    for u in reversed(units):
        if u["overlap"]:
            break
        pieces = _pieces(u["text"])
        sep = "\n" if u["text"].startswith("- ") else " "
        taken = []
        for p in reversed(pieces):
            if total >= n_words * 0.8:
                break
            # never take a piece that would blow far past the target
            if taken and total + _words(p) > n_words * 1.6:
                break
            taken.insert(0, p)
            total += _words(p)
        if taken:
            out.insert(0, {**u, "text": sep.join(taken), "overlap": True})
        if total >= n_words * 0.8:
            break
    return out


def _units(doc: dict, max_words: int) -> list[dict]:
    """Paragraph units, each tagged with its section heading."""
    units, h2, h3, new_h2 = [], None, None, False
    for block in doc["text"].split("\n\n"):
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^(#{2,6})\s+(.*)$", block)
        if m:
            if len(m.group(1)) <= 2:
                h2, h3, new_h2 = m.group(2), None, True
            else:
                h3 = m.group(2)
            continue
        section = f"{h2} > {h3}" if h2 and h3 else (h2 or h3 or "Introduction")
        for piece in _split_long(block, max_words):
            units.append({"text": piece, "section": section, "new_h2": new_h2, "overlap": False})
            new_h2 = False
    return units


def _render(units: list[dict]) -> str:
    """Join units; re-insert a heading line when the section changes mid-chunk."""
    parts, prev = [], None
    for u in units:
        if prev is not None and u["section"] != prev:
            parts.append("## " + u["section"])
        parts.append(u["text"])
        prev = u["section"]
    return "\n\n".join(parts)


def _rebalance(prev: list[dict], last: list[dict], min_words: int, max_words: int,
               overlap: int) -> list[list[dict]]:
    """Move trailing paragraphs from prev into a too-short final chunk, keeping both within limits."""
    body = [x for x in prev if not x["overlap"]] + [x for x in last if not x["overlap"]]
    lead = [x for x in prev if x["overlap"]]
    best = [prev, last]
    best_gap = min_words - _words(_render(last))
    for cut in range(len(body) - 1, 0, -1):
        a = lead + body[:cut]
        if not any(not x["overlap"] for x in a) or _words(_render(a)) < min_words:
            break
        b = _tail(a, overlap) + body[cut:]
        if _words(_render(b)) > max_words:
            b = body[cut:]
        if _words(_render(b)) > max_words:
            break
        gap = max(0, min_words - _words(_render(b)))
        if gap < best_gap:
            best, best_gap = [a, b], gap
        if gap == 0:
            break
    return best


def make_chunks(docs: list[dict], min_words: int = MIN_WORDS, max_words: int = MAX_WORDS,
                overlap: int = OVERLAP_WORDS) -> list[dict]:
    chunks = []
    for doc in docs:
        groups: list[list[dict]] = []
        cur: list[dict] = []
        for u in _units(doc, max_words - overlap - 10):
            n = _words(_render(cur))
            body = sum(_words(x["text"]) for x in cur if not x["overlap"])
            # max_words is the hard cap; min_words is the preferred size before a section break.
            too_big = _words(_render(cur + [u])) > max_words and body >= TAIL_MERGE_WORDS
            if _words(_render(cur + [u])) > max_words and not too_big:
                cur = [x for x in cur if not x["overlap"]]  # drop overlap rather than break the cap
            section_break = u["new_h2"] and n >= min_words
            if too_big or section_break:
                groups.append(cur)
                cur = _tail(cur, overlap)
                if _words(_render(cur + [u])) > max_words:
                    cur = []  # overlap + a long paragraph would break the cap; drop the overlap
            cur.append(u)
        if any(not x["overlap"] for x in cur):
            body = [x for x in cur if not x["overlap"]]
            merged = groups[-1] + body if groups else None
            if merged and _words(_render(merged)) <= max_words:
                groups[-1] = merged
            else:
                groups.append(cur)
        if len(groups) >= 2 and _words(_render(groups[-1])) < min_words:
            groups[-2:] = _rebalance(groups[-2], groups[-1], min_words, max_words, overlap)

        for i, g in enumerate(groups, 1):
            first_body = next(x for x in g if not x["overlap"])
            text = _render(g)
            chunks.append({
                "chunk_id": f"{doc['id']}_chunk_{i:02d}",
                "doc_id": doc["id"],
                "title": doc["title"],
                "url": doc["url"],
                "updated": doc["updated"],
                "topic": doc["topic"],
                "section": first_body["section"],
                "headings": list(dict.fromkeys(x["section"] for x in g)),
                "text": text,
                "word_count": _words(text),
            })
    return chunks


def save_chunks(chunks: list[dict], path: Path = CHUNKS_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    _refuse_eval_path(path)
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# -------------------------------------------------------------------- BM25

STOPWORDS = set("""
a an and are as at be been but by can could do does did for from had has have how i if in into
is it its me my of on or our should so than that the their them then there these they this
to was we were what when where which who why will with would you your yours about am any
""".split())


def _stem(t: str) -> str:
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("sses"):
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        t = t[:-1]
    if len(t) > 7 and t.endswith("ness"):  # nearsightedness -> nearsight(ed) -> nearsight
        t = t[:-4]
    if len(t) > 7 and t.endswith("tion"):  # injection -> inject, infection -> infect
        return t[:-3]
    if len(t) > 5 and t.endswith("ing"):
        return t[:-3]
    if len(t) > 4 and t.endswith("ed"):
        return t[:-2]
    return t


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


# Lay wording -> corpus wording. Applied to the query only, at reduced weight, so the
# literal question terms still dominate. Keep this short and general: every entry
# should be a vocabulary gap seen in real questions, not a fix for one eval item.
LAY_TERMS = {
    "shot": "inject injection",
    "restor": "undo reverse cure",
    "reversible": "undo reverse cure",
    "serious": "vision loss blindness emergency right away",
    "dangerous": "emergency right away serious",
    "sugar": "diabetes",
    "contagious": "spread",
    "goopy": "discharge",
    "crusty": "discharge",
    "blurry": "blurry vision",
    # Symptom location words: lay "center/middle" vs corpus "central vision"/"macula".
    "center": "central macula",
    "middle": "central macula",
    "spot": "blank blind",
}
EXPANSION_WEIGHT = 0.5

# Below this top-k coverage, treat retrieval as "no good evidence" (see is_weak).
# Picked from the eval sets in data/eval/; re-check whenever the corpus changes.
WEAK_COVERAGE = 0.5


def normalize(s: str) -> str:
    """Fold curly quotes and whitespace so hand-typed quotes match corpus text."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip()


def query_terms(question: str, expand: bool = True) -> dict[str, float]:
    """Query tokens with weights: 1.0 for the user's words, EXPANSION_WEIGHT for lay-term additions."""
    terms: dict[str, float] = {}
    for t in tokenize(question):
        terms[t] = terms.get(t, 0) + 1.0
        if expand and t in LAY_TERMS:
            for e in tokenize(LAY_TERMS[t]):
                terms.setdefault(e, 0)
                terms[e] = max(terms[e], EXPANSION_WEIGHT)
    return terms


def index_text(chunk: dict) -> str:
    """What BM25 sees: title and headings plus passage body."""
    return " ".join([chunk["title"], " ".join(chunk["headings"]), chunk["text"]])


class BM25Index:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.tfs = [Counter(tokenize(index_text(c))) for c in chunks]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / len(self.lens)
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def scores(self, query: str, expand: bool = True) -> list[float]:
        q = query_terms(query, expand)
        out = []
        for tf, dl in zip(self.tfs, self.lens):
            s = 0.0
            for t, w in q.items():
                f = tf.get(t)
                if f:
                    s += w * self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append(s)
        return out

    def coverage(self, query: str, i: int) -> float:
        """IDF-weighted share of the user's own query terms that appear in chunk i (0-1).

        Words absent from the whole corpus get the maximum IDF, so a question about
        something the corpus never mentions ("TV") scores low coverage everywhere.
        A lay term counts as present when any of its LAY_TERMS translations is.
        """
        terms = set(tokenize(query))
        if not terms:
            return 0.0
        max_idf = max(self.idf.values())
        tf = self.tfs[i]
        weights = {t: self.idf.get(t, max_idf) for t in terms}
        found = sum(w for t, w in weights.items()
                    if t in tf or any(e in tf for e in tokenize(LAY_TERMS.get(t, ""))))
        return found / sum(weights.values())


def build_index(chunks: list[dict] | None = None) -> BM25Index:
    if chunks is None:
        chunks = load_chunks() if CHUNKS_PATH.exists() else make_chunks(load_documents())
    return BM25Index(chunks)


_INDEX: BM25Index | None = None


def retrieve(question: str, k: int = 4, index: BM25Index | None = None,
             expand: bool = True) -> list[dict]:
    """Top-k passages with metadata, rank, BM25 score and query coverage.

    score: BM25 ranking score. Only meaningful for ordering results of one question;
        not a probability, not comparable across questions, not a measure of correctness.
    coverage: share (0-1, IDF-weighted) of the question's own words found in the passage.
        A rough "is this even on topic" signal; use is_weak() on the result list.
    """
    global _INDEX
    if index is None:
        if _INDEX is None:
            _INDEX = build_index()
        index = _INDEX
    scores = index.scores(question, expand)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [{**index.chunks[i], "rank": r, "score": round(scores[i], 3),
             "coverage": round(index.coverage(question, i), 3)}
            for r, i in enumerate(order, 1) if scores[i] > 0]


def is_weak(results: list[dict], threshold: float = WEAK_COVERAGE) -> bool:
    """True when no retrieved passage covers enough of the question to count as evidence."""
    return not results or max(r["coverage"] for r in results) < threshold


# --------------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--build", action="store_true", help="rebuild chunks.jsonl from documents.jsonl")
    ap.add_argument("-k", type=int, default=4)
    args = ap.parse_args()

    if args.build or not CHUNKS_PATH.exists():
        chunks = make_chunks(load_documents())
        save_chunks(chunks)
        wc = [c["word_count"] for c in chunks]
        off = [f"{c['chunk_id']}({c['word_count']})" for c in chunks
               if not MIN_WORDS <= c["word_count"] <= MAX_WORDS]
        print(f"wrote {len(chunks)} chunks -> {CHUNKS_PATH.relative_to(ROOT)} "
              f"(words min {min(wc)}, median {sorted(wc)[len(wc)//2]}, max {max(wc)})")
        print(f"{len(off)} chunks outside {MIN_WORDS}-{MAX_WORDS} words: {', '.join(off)}")
    if args.question:
        results = retrieve(args.question, k=args.k)
        if is_weak(results):
            print(f"WEAK EVIDENCE: no passage covers >= {WEAK_COVERAGE:.0%} of the question; "
                  "the corpus probably does not answer it.")
        for r in results:
            print(f"\n#{r['rank']} {r['chunk_id']}  score={r['score']}  cov={r['coverage']}  "
                  f"[{r['title']} > {r['section']}]")
            print("   " + r["text"][:300].replace("\n", " ") + " …")


if __name__ == "__main__":
    main()
