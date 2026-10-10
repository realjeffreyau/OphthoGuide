"""Build OphthoGuide LoRA training/validation data in mlx-lm chat format.

Usage: .venv/bin/python scripts/build_training_data.py

Every example = the app's SYSTEM_PROMPT + build_user_message(question, retrieved evidence)
+ a target response assembled from verbatim source sentences (extractive) plus a few fixed
framing sentences. Targets are re-checked against the evidence *as rendered in the prompt*.

Outputs: data/training/train.jsonl, valid.jsonl (messages only) and review_notes.jsonl.
"""

import json
import random
import re
import runpy
import sys
from collections import Counter
from pathlib import Path

from assistant import SYSTEM_PROMPT, _plain, _quote_in_passage, build_user_message, retrieve_evidence
from build_test_cases import _jaccard
from retrieval import load_chunks, load_documents

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "training"
SPECS = runpy.run_path(str(OUT_DIR / "src" / "specs.py"))
TEST_Q = [json.loads(l)["question"] for l in (ROOT / "data/evaluation/test_cases.jsonl").read_text().splitlines()]

TARGET = {"train": {"explain": 150, "clarify": 50, "abstain": 40, "premise": 30, "urgent": 30},
          "valid": {"explain": 25, "clarify": 8, "abstain": 7, "premise": 5, "urgent": 5}}
MAX_TOKENS = 1800
DISCLAIMER = "This is general education, not a diagnosis."
FRAMING = {  # fixed, non-medical sentences allowed without a citation
    DISCLAIMER,
    "I can't tell what's causing this from your question alone, but my sources mention a few possibilities.",
    "To narrow it down:",
    "I can't tell what's causing this from your question alone, and my sources didn't return passages that cover it.",
    "If your symptoms are severe or came on suddenly, please see an eye doctor promptly.",
    "Please get care now.", "Please get your eye checked now.", "Please contact your eye doctor now.",
    "Please contact your baby's doctor now.", "Please see your eye doctor right away.",
    "Not quite.", "Not according to my sources.", "No.", "That's not right.", "Not necessarily.",
    "Usually not.", "Not always.", "Not exactly.",
}
SEED = 20261008
# What the human (Claude) review covered, per behaviour (see data/training/README.md).
MANUAL_REVIEW = {
    "urgent": "read in full: all candidates; leads with care instruction; lists complete; ok",
    "premise": "read in full: all candidates; premise explicitly corrected from source; ok",
    "abstain": "read in full: all candidates; 1 flawed item (partly covered topic) removed; ok",
    "clarify": "curated per-symptom content read in full (16 symptoms) + empty-evidence template; ok",
    "explain": "auto-verified extractive; 40-example random sample + all list cases read; lists made complete",
}

CHUNKS = load_chunks()
BY_ID = {c["chunk_id"]: c for c in CHUNKS}
DOCS = {d["id"]: d for d in load_documents()}

_TOK = None


def tokens(messages):
    global _TOK
    if _TOK is None:
        from mlx_lm import load
        _TOK = load("Qwen/Qwen3-4B-MLX-4bit")[1]
    return len(_TOK.apply_chat_template(messages, tokenize=True))


def near_test(q):
    return max(_jaccard(q, t) for t in TEST_Q) >= 0.6


# ------------------------------------------------------------------ text units

def units_of(text):
    """Sentences and list items of a passage/section, in order."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or block.startswith("#"):
            continue
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("- "):
                out.append(("item", line[2:].strip()))
            elif line:
                out += [("sent", s.strip()) for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", line) if s.strip()]
    return out


def find_chunk(doc_id, quote, prefer=()):
    for c in list(prefer) + CHUNKS:
        if c["doc_id"] != doc_id:
            continue
        if len(quote.split()) < 3:  # short quotes ("Symptoms include"): exact match on a whole unit start
            if any(_plain(t).startswith(_plain(quote)) for _, t in units_of(BY_ID[c["chunk_id"]]["text"])):
                return BY_ID[c["chunk_id"]]
        elif _quote_in_passage(quote, c):
            return BY_ID[c["chunk_id"]]
    return None


def ensure_supplied(results, chunk, protect=()):
    """Return (results, injected). Replace the lowest-ranked passage that isn't protected
    (already needed by the target) if chunk isn't supplied yet."""
    if any(r["chunk_id"] == chunk["chunk_id"] for r in results):
        return results, False
    out = list(results)
    if len(out) < 4:
        return out + [dict(chunk)], True
    for i in range(len(out) - 1, -1, -1):
        if out[i]["chunk_id"] not in protect:
            out[i] = dict(chunk)
            return out, True
    raise ValueError("no replaceable passage")


def cite(text, cid):
    text = text.rstrip()
    if text[-1] in ".!?:":
        return f"{text[:-1]} [{cid}]{text[-1]}"
    return f"{text} [{cid}]."


def cap(s):
    return s[:1].upper() + s[1:]


# ------------------------------------------------------------------ trimming to the token budget

def trim_results(results, cited, keep_texts, budget_fn):
    rs = [dict(r) for r in results]
    if budget_fn(rs) <= MAX_TOKENS:
        return rs, False
    for n_keep in (4, 3, 2, 1):  # shorten uncited passages to their first n units
        for r in rs:
            if r["chunk_id"] not in cited:
                us = units_of(BY_ID[r["chunk_id"]]["text"])[:n_keep]
                r["text"] = "\n".join(("- " + t) if k == "item" else t for k, t in us)
        if budget_fn(rs) <= MAX_TOKENS:
            return rs, True
    # then drop unquoted units from cited passages, one at a time from the longest,
    # never removing a quoted unit or the list items that follow a quoted list intro
    units = {}
    for r in rs:
        if r["chunk_id"] not in cited:
            continue
        us = units_of(BY_ID[r["chunk_id"]]["text"])
        need, in_list = [], False
        for k, t in us:
            quoted = any(_plain(t) in _plain(x) or _plain(x) in _plain(t) for x in keep_texts)
            if quoted:
                need.append(True)
                in_list = t.rstrip().endswith(":")
            else:
                need.append(in_list and k == "item")
                if k != "item":
                    in_list = False
        units[r["chunk_id"]] = [[k, t, n] for (k, t), n in zip(us, need)]

    def render(cid):
        return "\n".join(("- " + t) if k == "item" else t for k, t, _ in units[cid])
    while budget_fn(rs) > MAX_TOKENS:
        cands = [cid for cid in units if any(not n for _, _, n in units[cid])]
        if not cands:
            break
        cid = max(cands, key=lambda c: len(render(c)))
        lst = units[cid]
        j = max(i for i, (_, _, n) in enumerate(lst) if not n)
        del lst[j]
        for r in rs:
            if r["chunk_id"] == cid:
                r["text"] = render(cid)
    return rs, True


# ------------------------------------------------------------------ checks

def parse_evidence(user_msg):
    ev = {}
    body = user_msg.split("\n\nQuestion:\n")[0]
    for m in re.finditer(r"\[(nei_\d{3}_chunk_\d{2})\]\n(.*?)(?=\n\n\[nei_\d{3}_chunk_\d{2}\]\n|\n\nNote: |\Z)", body, re.S):
        title_line, _, text = m.group(2).partition("\n")
        ev[m.group(1)] = {"title": title_line, "section": "", "text": text}
    return ev


def check_target(target, user_msg, behaviour, empty):
    """Every non-framing unit must be (near-)verbatim in a passage cited in its paragraph."""
    problems = []
    ev = parse_evidence(user_msg)
    if "<think>" in target or re.search(r"\b(lorem|TODO|XXX|placeholder)\b", target, re.I):
        problems.append("placeholder/think text")
    if not target.rstrip().endswith(DISCLAIMER):
        problems.append("missing disclaimer")
    for para in [p for p in target.split("\n\n") if p.strip()]:
        ids = re.findall(r"\[(nei_\d{3}_chunk_\d{2})\]", para)
        bad = [i for i in ids if i not in ev]
        if bad:
            problems.append(f"cites unsupplied {bad}")
        for line in para.split("\n"):
            line = re.sub(r"\s*\[nei_\d{3}_chunk_\d{2}\]", "", line).strip()
            line = re.sub(r"^- ", "", line)
            line = re.sub(r"^From the page on [^:]+: ", "", line)
            for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", line):
                s = s.strip()
                if (not s or s in FRAMING or s.endswith("?") or s.startswith("To narrow it down:")
                        or behaviour == "abstain"):
                    continue
                unit = s.rstrip(".:")
                if len(unit.split()) < 3:  # short list item ("Stye", "Blurry vision"): exact word match
                    ok = any(re.search(rf"(^|\W){re.escape(_plain(unit))}(\W|$)", _plain(ev[i]["text"]))
                             for i in ids if i in ev)
                else:
                    ok = any(_quote_in_passage(unit, ev[i]) for i in ids if i in ev)
                if not ok:
                    problems.append(f"unsupported unit: {s[:70]!r}")
    if empty and re.search(r"\[nei_", target):
        problems.append("citations with empty evidence")
    if behaviour == "urgent" and not re.match(r"Please (get|contact|see)", target):
        problems.append("urgent target must lead with the care instruction")
    return problems


# ------------------------------------------------------------------ builders

def rewrite(q, rng):
    """Vary phrasing for about half the heading-questions."""
    if rng.random() >= 0.5:
        return q
    rules = [
        (r"^What are the symptoms of (.+)\?$", r"What symptoms can \1 cause?"),
        (r"^What causes (.+)\?$", r"Why does \1 happen?"),
        (r"^Am I at risk for (.+)\?$", r"Who is more likely to get \1?"),
        (r"^How will my eye doctor check for (.+)\?$", r"How do eye doctors check for \1?"),
        (r"^What(?:’s|'s| is) the treatment for (.+)\?$", r"How is \1 treated?"),
        (r"^How can I prevent (.+)\?$", r"Can \1 be prevented?"),
    ]
    for pat, rep in rules:
        if re.match(pat, q):
            return re.sub(pat, rep, q)
    return q


def sections():
    out = []
    for d in DOCS.values():
        parts = re.split(r"^(#{2,3} .+)$", d["text"], flags=re.M)
        for i in range(1, len(parts) - 1, 2):
            head = parts[i].lstrip("# ").strip()
            body = parts[i + 1]
            if (head.endswith("?") and "latest research" not in head.lower()
                    and not head.lower().startswith(("did you know", "wondering", "need help"))):
                out.append((d["id"], head, body))
    return out


def build_explain(doc_id, heading, body, rng):
    q = rewrite(heading, rng)
    if near_test(q) or near_test(heading):
        return None
    picked, words, us, i = [], 0, units_of(body), 0
    while i < len(us):
        if us[i][0] == "item":  # never cut a list short: a partial list reads as complete
            run = []
            while i < len(us) and us[i][0] == "item" and len(run) < 12:
                run.append(us[i])
                i += 1
            picked += run
            words += sum(len(t.split()) for _, t in run)
        else:
            picked.append(us[i])
            words += len(us[i][1].split())
            i += 1
        if words >= 45 or sum(1 for k, _ in picked if k == "sent") >= 5:
            if i < len(us) and us[i][0] == "item" and picked[-1][1].endswith(":"):
                continue  # finish the list this sentence introduces
            break
    if words < 15:
        return None
    if picked[-1][1].endswith(":"):  # never end on a dangling list intro
        picked = picked[:-1]
    results, weak = retrieve_evidence(q)
    if weak or not picked:
        return None
    injected, homes = False, []
    for kind, t in picked:
        c = find_chunk(doc_id, t.rstrip(":"), prefer=results)
        if c is None:
            return None
        if all(r["chunk_id"] != c["chunk_id"] for r in results):
            results, inj = ensure_supplied(results, c, protect=set(homes))
            injected = injected or inj
        homes.append(c["chunk_id"])
    if set(homes) - {r["chunk_id"] for r in results}:
        return None  # two injected chunks would displace each other; skip
    paras, para, i = [], [], 0
    while i < len(picked):
        kind, t = picked[i]
        if kind == "sent":
            para.append(t if t.endswith(":") else cite(t, homes[i]))
            i += 1
            continue
        run = []
        while i < len(picked) and picked[i][0] == "item":
            run.append((picked[i][1], homes[i]))
            i += 1
        # cite at the last item of each chunk segment, so items from different chunks keep their own source
        items = [f"- {cite(t, h)}" if (j == len(run) - 1 or run[j + 1][1] != h) else f"- {t}"
                 for j, (t, h) in enumerate(run)]
        # the list shares a paragraph with its intro sentence so the citation scope covers both
        paras.append((" ".join(para) + "\n" if para else "") + "\n".join(items))
        para = []
    if para:
        paras.append(" ".join(para))
    target = "\n\n".join(paras + [DISCLAIMER])
    return dict(question=q, results=results, target=target, injected=injected,
                quotes=[t for _, t in picked], cited=set(homes), source=f"{doc_id}: {heading}")


def build_clarify(q, key):
    if near_test(q):
        return None
    pattern, questions = SPECS["SYMPTOMS"][key]
    results, weak = retrieve_evidence(q)
    if weak:  # the app supplies NO USABLE EVIDENCE: ask, don't guess, no citations
        target = "\n\n".join([
            "I can't tell what's causing this from your question alone, and my sources didn't return passages "
            "that cover it.",
            "To narrow it down: " + " ".join(questions[:3]),
            "If your symptoms are severe or came on suddenly, please see an eye doctor promptly.",
            DISCLAIMER])
        return dict(question=q, results=[], weak=True, target=target, injected=False, quotes=[], cited=set(),
                    source=f"symptom:{key}")
    poss_specs, flag_specs = SPECS["POSSIBILITIES"][key]
    poss, cited, quotes, injected = [], set(), [], False

    def place(doc, quote):
        nonlocal results, injected
        c = find_chunk(doc, quote, prefer=results)
        if c is None:
            raise ValueError(f"quote not in corpus: {doc} {quote[:60]!r}")
        if all(r["chunk_id"] != c["chunk_id"] for r in results):
            results, inj = ensure_supplied(results, c, protect=cited)
            injected = injected or inj
        cited.add(c["chunk_id"])
        quotes.append(quote)
        return c

    for doc, quote in poss_specs[:3]:
        c = place(doc, quote)
        poss.append(f"- From the page on {c['title']}: {cite(cap(quote), c['chunk_id'])}")
    parts = ["I can't tell what's causing this from your question alone, but my sources mention a few possibilities.\n"
             + "\n".join(poss),
             "To narrow it down: " + " ".join(questions[:3])]
    for doc, quote in flag_specs:
        c = place(doc, quote)
        us = units_of(c["text"])
        last = _plain(re.split(r"(?<=[.!?])\s+", quote)[-1])
        idx = next((i for i, (_, t) in enumerate(us) if _plain(t).startswith(last)), None)
        if idx is not None and us[idx][1].rstrip().endswith(":") and _plain(us[idx][1].rstrip().rstrip(":")) == last:
            items = []
            for kind, t in us[idx + 1:]:
                if kind != "item":
                    break
                items.append(t)
            lines = [f"- {t}" for t in items]
            lines[-1] = f"- {cite(items[-1], c['chunk_id'])}"
            parts.append(cap(quote) + ":\n" + "\n".join(lines))
        else:
            parts.append(cite(cap(quote), c["chunk_id"]))
    parts.append(DISCLAIMER)
    return dict(question=q, results=results, target="\n\n".join(parts), injected=injected,
                quotes=quotes, cited=cited, source=f"symptom:{key}")


def build_abstain(q, topic, referral, absent):
    if near_test(q):
        return None
    results, weak = retrieve_evidence(q)
    if weak or not results:
        target = f"My sources don't cover {topic}, so I can't answer this reliably. {referral}\n\n{DISCLAIMER}"
        return dict(question=q, results=[], weak=True, target=target, injected=False, quotes=[], cited=set(),
                    source=f"abstain:{topic}")
    if any(absent.lower() in _plain(r["text"]) for r in results):
        return None  # the passages may actually address it; not a clean abstain example
    titles = list(dict.fromkeys(r["title"] for r in results))
    about = ", ".join(titles[:-1]) + (" and " if len(titles) > 1 else "") + titles[-1]
    target = (f"The passages I found are about {about}, and they don't address {topic}, so I can't answer this "
              f"reliably from my sources. {referral}\n\n{DISCLAIMER}")
    return dict(question=q, results=results, target=target, injected=False, quotes=[], cited=set(),
                source=f"abstain:{topic}")


def build_quoted(q, lead, quotes, behaviour):
    if near_test(q):
        return None
    results, _weak = retrieve_evidence(q)
    injected, pieces, cited = False, [], set()
    for doc, quote in quotes:
        c = find_chunk(doc, quote, prefer=results)
        if c is None:
            raise ValueError(f"quote not in corpus: {doc} {quote[:60]!r}")
        if all(r["chunk_id"] != c["chunk_id"] for r in results):
            results, inj = ensure_supplied(results, c, protect=cited)
            injected = injected or inj
        us = units_of(c["text"])
        idx = next((i for i, (_, t) in enumerate(us) if _plain(t).startswith(_plain(quote)) or
                    (len(quote.split()) >= 3 and _plain(quote) in _plain(t))), None)
        unit = us[idx][1] if idx is not None else quote
        whole_intro = unit.rstrip().endswith(":") and _plain(unit.rstrip().rstrip(":")) == _plain(quote)
        if whole_intro or re.search(r"(if you have|if your baby has)$", quote):
            items = []  # the sentence continues as a list in the source: keep the list
            for kind, t in us[idx + 1:]:
                if kind != "item":
                    break
                items.append(t)
            lines = [f"- {t}" for t in items]
            lines[-1] = f"- {cite(items[-1], c['chunk_id'])}"
            pieces.append(cap(quote) + ":\n" + "\n".join(lines))
        else:
            pieces.append(cite(cap(quote), c["chunk_id"]))
        cited.add(c["chunk_id"])
    # keep source order; consecutive sentences share a paragraph, lists get their own
    paras, cur = [], [lead]
    for p in pieces:
        if "\n" in p:
            paras.append(" ".join(cur))
            cur = []
            paras.append(p)
        else:
            cur.append(p)
    if cur:
        paras.append(" ".join(cur))
    target = "\n\n".join([x for x in paras if x.strip()] + [DISCLAIMER])
    return dict(question=q, results=results, target=target, injected=injected,
                quotes=[qq for _, qq in quotes], cited=cited, source=behaviour)


# ------------------------------------------------------------------ assemble

def finalize(ex, behaviour, split, idx):
    weak = ex.get("weak", False)
    results = ex["results"]

    def budget(rs):
        return tokens([{"role": "system", "content": SYSTEM_PROMPT},
                       {"role": "user", "content": build_user_message(ex["question"], rs, weak)},
                       {"role": "assistant", "content": ex["target"]}])
    trimmed = False
    if results:
        results, trimmed = trim_results(results, ex["cited"], ex["quotes"], budget)
    user = build_user_message(ex["question"], results, weak)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user},
                {"role": "assistant", "content": ex["target"]}]
    n_tok = tokens(messages)
    if weak or not results:
        ev_type = "empty"
    elif not ex["cited"]:
        ev_type = "irrelevant"
    elif len(ex["cited"]) < len(results):
        ev_type = "useful+irrelevant"
    else:
        ev_type = "useful"
    problems = check_target(ex["target"], user, behaviour, ev_type == "empty")
    if n_tok > MAX_TOKENS:
        problems.append(f"over token budget ({n_tok})")
    note = {"id": f"{split}_{idx:03d}", "split": split, "behaviour": behaviour, "question": ex["question"],
            "source": ex["source"], "evidence_type": ev_type, "supplied": [r["chunk_id"] for r in results],
            "cited": sorted(ex["cited"]), "injected_passage": ex["injected"], "evidence_trimmed": trimmed,
            "tokens": n_tok, "auto_check": problems or "pass", "manual_review": MANUAL_REVIEW[behaviour],
            "clinical_review": "pending"}
    return {"messages": messages}, note


def main():
    rng = random.Random(SEED)
    pools = {b: [] for b in ["explain", "clarify", "abstain", "premise", "urgent"]}
    secs = sections()
    rng.shuffle(secs)
    for doc_id, head, body in secs:
        ex = build_explain(doc_id, head, body, rng)
        # one example per near-identical question (e.g. two pink-eye pages share a heading)
        if ex and all(_jaccard(ex["question"], o["question"]) < 0.85 for o in pools["explain"]):
            pools["explain"].append(ex)
    for q, key, _g in SPECS["MISSING"]:
        ex = build_clarify(q, key)
        if ex:
            pools["clarify"].append(ex)
    for q, topic, ref, absent in SPECS["ABSTAIN"]:
        ex = build_abstain(q, topic, ref, absent)
        if ex:
            pools["abstain"].append(ex)
    for q, opener, quotes, _g in SPECS["PREMISE"]:
        ex = build_quoted(q, opener, quotes, "premise")
        if ex:
            pools["premise"].append(ex)
    for q, key, _g in SPECS["URGENT"]:
        lead, quotes = SPECS["SCENARIOS"][key]
        ex = build_quoted(q, lead, quotes, "urgent")
        if ex:
            pools["urgent"].append(ex)

    print("pool sizes:", {k: len(v) for k, v in pools.items()})
    # take candidates in shuffled order; an example that cannot pass the checks within the
    # token budget is skipped (never truncated) and the next candidate is used instead
    rows = {"train": [], "valid": []}
    skipped = []
    for b, pool in pools.items():
        rng.shuffle(pool)
        accepted = []
        for ex in pool:
            if len(accepted) == TARGET["valid"][b] + TARGET["train"][b]:
                break
            _, note = finalize(ex, b, "check", 0)
            if note["auto_check"] == "pass":
                accepted.append(ex)
            else:
                skipped.append((b, ex["question"], note["auto_check"]))
        need_v, need_t = TARGET["valid"][b], TARGET["train"][b]
        if len(accepted) < need_v + need_t:
            print(f"ERROR not enough passing {b}: {len(accepted)} < {need_v + need_t}")
            return 1
        rows["valid"] += [(b, ex) for ex in accepted[:need_v]]
        rows["train"] += [(b, ex) for ex in accepted[need_v:]]
    for b, q, why in skipped:
        print(f"SKIPPED {b}: {q} -> {why}")

    train_q = [ex["question"] for _, ex in rows["train"]]
    # sections/scenario questions never repeat across splits (one example per section); flag true near-copies
    dups = [ex["question"] for _, ex in rows["valid"] if max(_jaccard(ex["question"], t) for t in train_q) >= 0.85]
    for d in dups:
        print("ERROR valid question near-duplicates a train question:", d)

    notes = []
    for split in ("train", "valid"):
        rng.shuffle(rows[split])
        out = []
        for i, (b, ex) in enumerate(rows[split], 1):
            rec, note = finalize(ex, b, split, i)
            out.append(rec)
            notes.append(note)
        (OUT_DIR / f"{split}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                                                encoding="utf-8")
    (OUT_DIR / "review_notes.jsonl").write_text("".join(json.dumps(n, ensure_ascii=False) + "\n" for n in notes),
                                                encoding="utf-8")
    bad = [n for n in notes if n["auto_check"] != "pass"]
    for n in bad:
        print("AUTO-CHECK FAIL", n["id"], n["behaviour"], n["auto_check"])
    for split in ("train", "valid"):
        ns = [n for n in notes if n["split"] == split]
        print(split, len(ns), dict(Counter(n["behaviour"] for n in ns)), dict(Counter(n["evidence_type"] for n in ns)),
              "| max tokens", max(n["tokens"] for n in ns), "| injected", sum(n["injected_passage"] for n in ns),
              "| trimmed", sum(n["evidence_trimmed"] for n in ns))
    return 1 if (bad or dups) else 0


if __name__ == "__main__":
    sys.exit(main())
