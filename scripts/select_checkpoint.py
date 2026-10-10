"""Choose a LoRA checkpoint using the validation set only.

For the base model and every saved checkpoint of a run, generate answers for the 50
validation prompts exactly as stored in data/training/valid.jsonl (same system prompt,
temp 0.2, top_p 0.9, max 700 tokens, a fixed seed per example), then run the automatic
checks from score_versions.py.

Selection rule (fixed before looking at results):
  1. most validation answers with the expected action (heuristic classifier);
  2. then fewest problems: invalid citations + citations on empty evidence +
     low-support cited sentences + repetitive answers;
  3. then lowest validation loss from the training log.
The winner is copied to adapters/selected/ with SELECTED.json explaining the choice.

  .venv/bin/python scripts/select_checkpoint.py --run adapters/run_01 [--select]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import assistant  # noqa: E402
from run_versions import case_seed  # noqa: E402
from score_versions import BEHAVIOUR_ACTION, check, load_chunks  # noqa: E402

VALID = ROOT / "data/training/valid.jsonl"
NOTES = ROOT / "data/training/review_notes.jsonl"
OUT_DIR = ROOT / "data/results/checkpoints"


def val_losses(run: Path) -> dict[int, float]:
    log = re.sub(r"\x1b\[[0-9;]*m", "", (run / "train.log").read_text(encoding="utf-8"))
    return {int(m.group(1)): float(m.group(2))
            for m in re.finditer(r"^\s*(\d+)\s+val\s+([\d.]+)", log, re.M)}


def generate_all(adapter_dir: str | None, out: Path) -> list[dict]:
    if out.exists():
        return [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    notes = [n for n in map(json.loads, NOTES.read_text(encoding="utf-8").splitlines())
             if n["split"] == "valid"]
    rows = [json.loads(l) for l in VALID.read_text(encoding="utf-8").splitlines()]
    assistant.configure(adapter_dir)
    recs = []
    for n, r in zip(notes, rows):
        system, user = r["messages"][0]["content"], r["messages"][1]["content"]
        text = assistant.generate_answer(system, user, seed=case_seed(n["id"]))
        recs.append({"id": n["id"], "behaviour": n["behaviour"], "evidence_type": n["evidence_type"],
                     "supplied": n["supplied"], "answer": text, "target": r["messages"][2]["content"]})
        print(f"  {n['id']} {len(text.split())}w", flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in recs), encoding="utf-8")
    return recs


def evaluate(recs: list[dict], chunks: dict) -> dict:
    ok = problems = 0
    by = {}
    for r in recs:
        empty = r["evidence_type"] == "empty"
        c = check(r["answer"], [] if empty else [chunks[i] for i in r["supplied"]], empty)
        hit = c["action"] == BEHAVIOUR_ACTION[r["behaviour"]]
        ok += hit
        a, b = by.get(r["behaviour"], (0, 0))
        by[r["behaviour"]] = (a + hit, b + 1)
        problems += (bool(c["invalid_cites"]) + c["cites_on_empty"] + c["low_support"]
                     + (c["repetition"] > 0.2))
    words = sorted(len(r["answer"].split()) for r in recs)
    return {"action_ok": ok, "n": len(recs), "problems": problems,
            "by_behaviour": {k: f"{a}/{b}" for k, (a, b) in sorted(by.items())},
            "median_words": words[len(words) // 2]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--select", action="store_true", help="copy the winner to adapters/selected")
    args = ap.parse_args()
    run = args.run if args.run.is_absolute() else ROOT / args.run
    chunks = load_chunks()
    losses = val_losses(run)
    ckpts = sorted(run.glob("*_adapters.safetensors"))
    results = {"base": evaluate(generate_all(None, OUT_DIR / "base.jsonl"), chunks)}
    print("base", results["base"], flush=True)
    for ck in ckpts:
        it = int(ck.name.split("_")[0])
        name = f"{run.name}_{it:04d}"
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(run / "adapter_config.json", tmp)
            shutil.copy(ck, Path(tmp) / "adapters.safetensors")
            recs = generate_all(tmp, OUT_DIR / f"{name}.jsonl")
        res = evaluate(recs, chunks)
        res["val_loss"] = losses.get(it)
        results[name] = res
        print(name, res, flush=True)
    assistant.configure(None)
    (OUT_DIR / f"{run.name}_summary.json").write_text(json.dumps(results, indent=1), encoding="utf-8")

    cands = [k for k in results if k != "base"]
    if not cands:
        sys.exit("no checkpoints found")
    best = min(cands, key=lambda k: (-results[k]["action_ok"], results[k]["problems"],
                                     results[k]["val_loss"] if results[k]["val_loss"] is not None else 9e9))
    print("best:", best, results[best])
    if args.select:
        it = int(best.rsplit("_", 1)[1])
        dest = ROOT / "adapters/selected"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(run / "adapter_config.json", dest)
        shutil.copy(run / f"{it:07d}_adapters.safetensors", dest / "adapters.safetensors")
        (dest / "SELECTED.json").write_text(json.dumps(
            {"run": run.name, "iteration": it, "rule": "max validation action_ok, then fewest "
             "problems, then lowest val loss", "scores": results[best], "base": results["base"]},
            indent=1), encoding="utf-8")
        print("copied ->", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
