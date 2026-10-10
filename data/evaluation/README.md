# OphthoGuide evaluation set: frozen, test only

> **Do not train on this, and do not index it.** `test_cases.jsonl` must never be used for training, fine-tuning, few-shot examples or prompt tuning. It must never be added to the retrieval index. The NEI source documents stay searchable during testing; the test cases and reference answers do not.

## Files

| File | Contents |
|---|---|
| `test_cases.jsonl` | 150 cases: the frozen artifact |
| `MANIFEST.json` | sha256, version, counts, corpus hashes, review status |
| `RUBRIC.md` | How to score answers: 6 dimensions, 2 critical gates, pass rule, reporting |
| `src/cases_*.py` | Human-readable case sources |
| `../../scripts/build_test_cases.py` | Builds, validates and freezes the set |

## Case fields
- **Required fields:** `id`, `category`, `question`, `reference_answer`, `required_facts`, `unacceptable_claims`, `expected_action` (answer / clarify / escalate / abstain), `supporting_source_ids`.
- **Extra fields:**
  - `evidence`: a verbatim source quote for each required fact, checked automatically against `documents.jsonl`;
  - `clarifying_questions`: for clarify cases;
  - `group_id`: paraphrases share one;
  - `split`: always `"test"`;
  - `review`: clinical review status.

## Composition

| Category | n | Expected actions |
|---|---|---|
| straightforward | 60 | answer |
| missing_info | 30 | clarify (28), answer (2) |
| urgent | 20 | escalate |
| false_premise | 20 | answer (16), abstain (3), escalate (1) |
| out_of_scope | 20 | abstain |

**Paraphrase groups.** There are 8 groups of 2: cataract spread, AMD blindness, antibiotics for viral pink eye, red eye, acute angle-closure, post-op cataract pain, cataract-dissolving drops, and glaucoma drop dose. **Members of a group always stay in the same split.** If the set is ever split (e.g. dev/test), split by `group_id`, never by `id`.

## How the cases were written
- Every reference answer is written from the NEI pages in `data/processed/documents.jsonl` (50 pages), with source IDs in brackets.
- Every required fact carries a verbatim quote from the cited page. The build fails if any quote is missing from its source.
- Urgent cases use only scenarios where a page gives explicit "right away / emergency room / call now" guidance, and each reference leads with that instruction.
  - One draft urgent case (a newborn with cloudy eyes) was dropped because the source has no explicit urgency guidance for it.
- **Kept separate from tuning.** The build rejects any question with token-Jaccard ≥ 0.6 to the 56 questions used for retrieval and assistant tuning (`data/eval/`).

## Clinical review: **pending**
I (an AI) wrote these cases from NEI text. They have **not** been reviewed by a qualified clinician. Before treating results as safety evidence, have an ophthalmologist or optometrist review at least:
- all **urgent** cases: `tc_091`–`tc_110`, and `tc_129`, which is escalate inside false_premise. Check that the expected action and urgency level are right.
- all **missing_info** cases: `tc_061`–`tc_090`. Check the red flags and clarifying questions.

When a case is reviewed, set `review.clinical_review` to `approved` or `revised` in the source file, add the reviewer, then rebuild with `--refreeze` and note it in the changelog below.

## Known limitations
- **One source family (NEI), English only.** References reflect NEI wording as of the retrieval date. Some pages are older; for example, the AMD page was updated 2021-06-22.
- **One known source conflict.** Pink-eye duration is "7–10 days" in nei_008 (2025) and "1–2 weeks viral" in nei_046 (2019). tc_038 notes both.
- **One author, so cases may share blind spots.** Adding more items from other authors or real user questions would strengthen the set.
- **Topic overlap with tuning.** Some topics overlap with the tuning questions (e.g. retinal detachment symptoms), though no question is a near-duplicate. Scores on those topics may be slightly optimistic.

## Commands
```
.venv/bin/python scripts/build_test_cases.py               # rebuild + validate; refuses to change a frozen set
.venv/bin/python scripts/build_test_cases.py --verify      # file matches MANIFEST hash
.venv/bin/python scripts/build_test_cases.py --refreeze    # intentional change (record why below)
.venv/bin/python scripts/build_test_cases.py --check-train data/train/xxx.jsonl   # run on ANY training file before use
```

## Changelog
- **v1 (2026-10-08):** initial 150 cases.
- **v2 (2026-10-08, same session, before any model was evaluated on it):**
  - Removed three pieces of advice the sources don't support from reference answers: "take your contacts out" and "don't stop a prescribed medicine/steroid" (×2).
  - No questions, actions or facts changed.
