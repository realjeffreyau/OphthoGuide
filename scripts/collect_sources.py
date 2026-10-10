"""Collect NEI eye-health pages into data/processed/documents.jsonl.

Usage: .venv/bin/python scripts/collect_sources.py [--refresh]

Reads data/sources/nei_pages.csv (id,topic,url), caches raw HTML in data/raw/,
extracts main article text (headings kept as Markdown), checks reuse markers,
and writes documents.jsonl plus a collection report.
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
SOURCES_CSV = ROOT / "data" / "sources" / "nei_pages.csv"
RAW_DIR = ROOT / "data" / "raw"
OUT_JSONL = ROOT / "data" / "processed" / "documents.jsonl"
REPORT_MD = ROOT / "data" / "processed" / "collection_report.md"

USER_AGENT = "OphthoGuide-research-collector/0.1 (educational project; polite crawl)"
SOURCE_NAME = "National Eye Institute (NEI/NIH)"
ATTRIBUTION = "Courtesy: National Eye Institute, National Institutes of Health (NEI/NIH)."

# Page chrome that is not article content.
DROP_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside",
             "form", "figure", "figcaption", "img", "picture", "svg", "button",
             "iframe", "video", "audio"]
DROP_CLASS_PATTERNS = [
    r"c-jump-menu", r"c-print-page", r"breadcrumb", r"c-sidebar", r"c-share",
    r"c-last-updated", r"c-feedback", r"helpful", r"back-to-top", r"c-at-a-glance__image",
    r"visually-hidden", r"sr-only",
    r"\bc-link\b",  # "Learn more about ..." cross-link blocks
]
NAV_RESIDUE = [
    "Was this page helpful", "Back to top", "Skip to content", "Print this page",
    "NIH Websites Are Changing", "On this page",
]
# Sections that are campaign promos or download/link lists rather than health content.
# "Did you know?" is kept: it holds real facts.
PROMO_HEADING = re.compile(r"^(Healthy Aging Month|Featured Resource\b.*|.*\bResources)$", re.I)
# Markers suggesting third-party / copyrighted material inside the article.
REUSE_FLAGS = [
    r"©", r"\bcopyright", r"used with permission", r"reprinted", r"all rights reserved",
    r"courtesy of (?!the national eye institute|national eye institute|nei)",
]
BLOCK_TAGS = ["p", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "table", "blockquote", "dl"]


def fetch(url: str, cache: Path, refresh: bool) -> tuple[str, str]:
    """Return (html, final_url). Uses cache unless refresh."""
    meta = cache.with_suffix(".url")
    if cache.exists() and meta.exists() and not refresh:
        return cache.read_text(encoding="utf-8"), meta.read_text().strip()
    candidates = [url]
    if "/eye-health-information/" in url:
        candidates.append(url.replace("/eye-health-information/", "/learn-about-eye-health/"))
    last_err = None
    for cand in candidates:
        resp = requests.get(cand, headers={"User-Agent": USER_AGENT}, timeout=30)
        time.sleep(1.0)
        if resp.status_code == 200:
            cache.write_text(resp.text, encoding="utf-8")
            meta.write_text(resp.url)
            return resp.text, resp.url
        last_err = f"HTTP {resp.status_code} for {cand}"
    raise RuntimeError(last_err)


def parse_updated(soup: BeautifulSoup) -> str | None:
    block = soup.select_one(".c-last-updated")
    text = block.get_text(" ", strip=True) if block else ""
    m = re.search(r"Last updated:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if not m:
        meta = soup.find("meta", attrs={"property": re.compile("updated")}) or \
            soup.find("meta", attrs={"name": re.compile("updated")})
        if meta and meta.get("content"):
            m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", meta["content"])
    if not m:
        return None
    return dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()


def clean_inline(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    # get_text(" ") leaves gaps where inline links end: "cataracts ." -> "cataracts."
    s = re.sub(r"\s+([.,;:!?)\u2019])", r"\1", s)
    return re.sub(r"([(\u2018])\s+", r"\1", s)


def render(node: Tag, out: list[str]) -> None:
    """Walk the article tree, emitting Markdown-ish blocks."""
    for child in node.children:
        if not isinstance(child, Tag):
            continue
        name = child.name
        if re.fullmatch(r"h[1-6]", name):
            level = max(2, int(name[1]))
            txt = clean_inline(child.get_text(" "))
            if txt:
                out.append("#" * level + " " + txt)
        elif name in ("ul", "ol"):
            items, trailing = [], []
            for li in child.find_all("li", recursive=False):
                # A list item with several paragraphs (e.g. the "At a glance" Treatment item
                # followed by an emergency callout): keep the first in the item, emit the rest
                # as their own paragraphs so sentences don't run together.
                for extra in li.find_all("p")[1:]:
                    txt = clean_inline(extra.extract().get_text(" "))
                    if txt:
                        trailing.append(txt)
                txt = clean_inline(li.get_text(" "))
                if txt:
                    items.append("- " + txt)
            if items:
                out.append("\n".join(items))
            out.extend(trailing)
        elif name == "table":
            rows = []
            for tr in child.find_all("tr"):
                cells = [clean_inline(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                out.append("\n".join(rows))
        elif name in ("p", "blockquote", "dl"):
            txt = clean_inline(child.get_text(" "))
            if txt:
                out.append(txt)
        elif child.find(BLOCK_TAGS):
            # Container holding block elements: recurse.
            render(child, out)
        else:
            txt = clean_inline(child.get_text(" "))
            if txt:
                out.append(txt)


def drop_promo_sections(blocks: list[str]) -> list[str]:
    """Remove campaign/link-list sections (heading plus body up to the next heading of equal or higher level)."""
    out, skip_level = [], None
    for b in blocks:
        m = re.match(r"^(#+)\s+(.*)$", b)
        if m:
            level = len(m.group(1))
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and PROMO_HEADING.match(m.group(2)):
                skip_level = level
        if skip_level is None:
            out.append(b)
    return out


def extract(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    updated = parse_updated(soup)

    title_tag = soup.select_one("main h1") or soup.find("h1")
    title = clean_inline(title_tag.get_text(" ")) if title_tag else ""
    if not title and soup.title:
        title = soup.title.get_text().split("|")[0].strip()

    main = soup.select_one("main#main-content") or soup.find("main") or soup.body
    for tag in main.find_all(DROP_TAGS):
        tag.decompose()
    pattern = re.compile("|".join(DROP_CLASS_PATTERNS), re.I)
    for tag in main.find_all(True):
        if getattr(tag, "decomposed", False) or tag.attrs is None:
            continue
        cls = " ".join(tag.get("class") or []) + " " + (tag.get("id") or "")
        if pattern.search(cls):
            tag.decompose()
    # Link-only paragraphs are cross-links ("Learn more about cataract surgery"), not content.
    for p in main.find_all("p"):
        links = p.find_all("a")
        txt = clean_inline(p.get_text(" ")).rstrip(".:")
        if len(links) == 1 and clean_inline(links[0].get_text(" ")).rstrip(".:") == txt:
            p.decompose()

    blocks: list[str] = []
    render(main, blocks)

    # Drop the duplicated H1 title, nav residue, and consecutive duplicates.
    cleaned: list[str] = []
    for b in blocks:
        # Trailing cross-link sentence: "... swelling. Learn more about uveitis."
        b = re.sub(r"\s*Learn more about [^.\n]*[.:]?$", "", b, flags=re.M).strip()
        if not b:
            continue
        plain = b.lstrip("# ").strip()
        if plain == title and b.startswith("#"):
            continue
        if any(plain.startswith(r) for r in NAV_RESIDUE):
            continue
        if cleaned and cleaned[-1] == b:
            continue
        cleaned.append(b)
    text = "\n\n".join(drop_promo_sections(cleaned)).strip()
    return {"title": title, "updated": updated, "text": text}


def reuse_check(text: str) -> tuple[str, list[str]]:
    hits = []
    for pat in REUSE_FLAGS:
        for m in re.finditer(pat, text, re.I):
            s = max(0, m.start() - 60)
            hits.append(text[s:m.end() + 60].replace("\n", " "))
    return ("needs_review" if hits else "public_domain_verified"), hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="ignore HTML cache and refetch")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    retrieved = dt.date.today().isoformat()

    with SOURCES_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))

    docs, report, failures = [], [], []
    for row in rows:
        try:
            html, final_url = fetch(row["url"], RAW_DIR / f"{row['id']}.html", args.refresh)
        except (requests.RequestException, RuntimeError) as e:
            failures.append((row["id"], row["url"], str(e)))
            print(f"FAIL {row['id']} {e}", file=sys.stderr)
            continue
        ex = extract(html)
        reuse, hits = reuse_check(ex["text"])
        doc = {
            "id": row["id"],
            "title": ex["title"],
            "url": final_url,
            "updated": ex["updated"],
            "retrieved": retrieved,
            "topic": row["topic"],
            "reuse": reuse,
            "source": SOURCE_NAME,
            "attribution": ATTRIBUTION,
            "text": ex["text"],
        }
        docs.append(doc)
        words = len(ex["text"].split())
        heads = sum(1 for line in ex["text"].splitlines() if line.startswith("#"))
        report.append((doc, words, heads, hits))
        print(f"ok   {row['id']} {words:5d}w {heads:2d}h {reuse:22s} {ex['title']}")

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    lines = [
        "# Collection report",
        "",
        f"Retrieved: {retrieved}  ",
        f"Documents: {len(docs)} / {len(rows)}  ",
        "Reuse basis: NEI copyright policy (https://www.nei.nih.gov/web-policies/copyright-policy). "
        "Text only; images/illustrations excluded.",
        "",
        "| id | topic | title | updated | words | headings | reuse |",
        "|---|---|---|---|---|---|---|",
    ]
    for d, w, h, _ in report:
        lines.append(f"| {d['id']} | {d['topic']} | [{d['title']}]({d['url']}) | "
                     f"{d['updated'] or 'n/a'} | {w} | {h} | {d['reuse']} |")
    flagged = [(d, hits) for d, _, _, hits in report if hits]
    if flagged:
        lines += ["", "## Reuse flags (manual review)", ""]
        for d, hits in flagged:
            lines.append(f"- **{d['id']}** {d['title']}")
            lines += [f"  - `…{h}…`" for h in hits]
    if failures:
        lines += ["", "## Fetch failures", ""]
        lines += [f"- {i} {u}: {e}" for i, u, e in failures]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nwrote {len(docs)} docs -> {OUT_JSONL.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
