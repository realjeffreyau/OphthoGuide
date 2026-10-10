# Assistant answer review: 10 responses, every claim checked

**Setup**
- Model: Qwen3-4B-MLX-4bit, temperature 0.2, thinking off.
- Retrieval: the top 4 BM25 passages. When `is_weak()` is true, no passages are supplied and the prompt says so explicitly.
- Questions: `assistant_review_questions.jsonl`.
- Logs: `assistant_runs_v1.jsonl`, `assistant_runs_v2.jsonl` and `assistant_runs.jsonl` (v3, final).

**Method**
- I split each answer into individual medical claims and read the passage each claim cites.
- Each claim gets one verdict:
  - ✓ supported: the cited passage says it.
  - ◐ partial: true per the evidence, but with the wrong or invalid citation, a dropped qualifier, or a slight overstatement.
  - ○ uncited: no citation, but consistent with a supplied passage.
  - ✗ unsupported or contradicted.
- A valid citation does not mean the claim is supported. Several claims below cite a real, supplied passage that doesn't say what the answer claims.

## Iterations

| Version | Change | Problems found in review |
|---|---|---|
| v1 | System prompt given + citation rules | **a10:** "Yes, you can get LASIK with thin corneas", which is unsupported and potentially harmful. **a07:** invented the farsightedness mechanism under a valid citation. **a05:** "usually harmless" cited the retinal-detachment chunk. **a03:** dropped "most" and "ask your doctor". **a01/a03:** emergency boilerplate added to non-urgent questions. |
| v2 | Stricter rules: open with a supported answer, keep qualifiers, cite the passage that says it. Prompt now lists question terms missing from all passages. | **a10 fixed** (states the LASIK gap). Boilerplate got worse: 6 of 10 answers. **a09:** used the "safety guidance" label to slip in an uncited claim ("may cause eye strain"). **a02 regressed:** over-hedged and said the evidence doesn't address it, though chunk_04 says "won't undo any damage". |
| **v3** | **Safety moved into code:** urgent symptoms are detected from the question and a fixed notice is shown first, and any safety text the model writes is stripped. Added one worked example (unrelated topic) in the prompt. Added automatic checks (below). | Boilerplate gone. a02, a09 and a10 correct. Remaining errors are in the table below. |

The lesson: the 4B model doesn't reliably follow conditional rules ("only if… then…"). Anything safety-critical has to be deterministic code, not a prompt instruction.

## v3: claim-level review

| ID | Type | Claims | ✓ | ◐ | ○ | ✗ | Notes |
|---|---|---|---|---|---|---|---|
| a01 | Plain factual | 4 | 2 | 1 | 1 | 0 | "Early symptoms: none" ✓. "Halos" is real but lives in chunk_02; the answer cited chunk_01. |
| a02 | Negative answer | 2 | 2 | 0 | 0 | 0 | "No cure" [002_01] and "treatment won't undo any damage" [002_04]: both exact. |
| a03 | Recommendation + exception | 3 | 2 | 1 | 0 | 0 | "Most people with diabetes… at least once a year" and "ask your doctor" are kept ✓. "Diabetes increases risk…" is uncited and not in the cited chunk. |
| a04 | Urgent | 3 | 3 | 0 | 0 | 0 | Safety notice shown first. "Go to eye doctor or ER right away" [014_01] ✓. No follow-up questions delayed care ✓. |
| a05 | Benign + exception | 5 | 3 | 1 | 1 | 0 | Emergency signs [015_03] ✓. "Especially as people age" is real but in 015_02, while 015_01 was cited. Gives the exception before the usual case. |
| a06 | Lay terminology | 3 | 2 | 1 | 0 | 0 | Anti-VEGF injections and PDT ✓ (exact). "Treatments aim to stop further vision loss" dropped the passage's "**may** be able to". |
| a07 | Comparison | 5 | 2 | 1 | 1 | **1** | **✗ "Farsightedness: eyeball too short / cornea not curved enough, focus behind retina"** is in no supplied passage. Cited nei_009_chunk_02, which **was not supplied**; the checker flagged it and it is not shown as a source. Nearsightedness mechanism: true per 010_02 (supplied) but cited to the same invalid ID. |
| a08 | Personal diagnosis request | 6 | 2 | 2 | 0 | **2** | Good: doesn't diagnose, names an alternative condition (macular edema), points to a dilated exam. **✗ "these are early symptoms of cataracts"**: 001_01 lists them as *later* symptoms ("Early Symptoms: None"). **✗ "macular edema often presents with more sudden changes"**: contradicts 005_01 ("vision that gets worse over time"). Cited 005_04, which wasn't supplied (flagged). |
| a09 | Out of corpus | (gap) | n/a | n/a | n/a | n/a | No evidence supplied. States the gap, adds no outside claims ✓. |
| a10 | Partly covered | (gap) | n/a | n/a | n/a | n/a | States that LASIK and corneal thickness are not covered and names the gap ✓. No citations, which is correct here. |

**Totals over 31 checkable claims (a01–a08)**

| Verdict | Count | Share |
|---|---|---|
| ✓ supported | 18 | 58% |
| ◐ partial | 7 | 23% |
| ○ uncited but consistent | 3 | 10% |
| ✗ unsupported or contradicted | **3** | 10% |

- **Citation validity:** 12 of 14 cited IDs (86%) were passages actually supplied. Both invalid IDs were caught and left out of the source links.
- **Gap handling:** 2 of 2 correct (out of corpus and partly covered).
- **Urgent handling:** 1 of 1 correct, with care advice first. No emergency boilerplate on the 9 non-urgent questions.

## What the automatic checks catch, and what they miss

`assistant.py` attaches these warnings to every answer:

| Check | What it does | On v3 |
|---|---|---|
| **Invalid citation** | Lists cited IDs that weren't in the supplied evidence. They are marked in the answer and never rendered as sources. | Caught both: a07 (009_02) and a08 (005_04). |
| **Low word overlap** | Flags a cited sentence when fewer than 60% of its content words appear in the passage it cites. | Caught a05 "as people age" (wrong chunk), a01 "halos" (wrong chunk) and a08 "macular edema sudden" (contradiction). One false positive: a07's treatment sentence, which is correct. |
| **Uncited statement** | Lists sentences with no citation at all. | Listed the uncited claims in a01, a03, a04, a05, a06 and a07. |
| **Missing question terms** (in the prompt) | Tells the model which question words appear in no supplied passage. | Steered a10 to state the LASIK gap. |

**Missed by every check: a08 "these are early symptoms".** The words overlap heavily with the cited passage (blurry, faded, symptoms, cataracts, and even "early"), but the meaning is reversed. Lexical checks can't detect this. **Manual review, or a model-based entailment check, is still required.**

## Remaining failure patterns (for the next step)
1. **Wrong-but-plausible synthesis (a07, a08):** the model fills gaps with general knowledge or reverses a qualifier ("later" became "early"). The prompt alone hasn't fixed this. Options:
   - A claim-by-claim entailment check (a second model pass: "does passage X state claim Y?").
   - Constrained extractive answers: quote, then explain.
   - A larger model.
2. **Wrong passage cited for a true claim (a01, a05):** the right passage was supplied, but the model cited the neighbouring one. A per-sentence "best supporting passage" re-mapping using the overlap scores could auto-correct the citation.
3. **Dropped qualifiers ("may", "most"):** improved from v1, but still happens (a06).
4. **Order of usual case and exception (a05):** leads with the exception. This matters less for safety but can alarm users.
5. **Comparisons (a07):** retrieval surfaced only one side well (color blindness also ranked high), and the model filled in the other side. This ties back to retrieval failure F1.

## How to reproduce
```
.venv/bin/python scripts/assistant.py "question" --show-evidence
.venv/bin/python scripts/assistant.py "question" --dry-run          # exact prompt, no model
.venv/bin/python scripts/assistant.py --batch data/eval/assistant_review_questions.jsonl --log data/eval/assistant_runs.jsonl
```

Generation is sampled (temperature 0.2), so re-runs vary slightly. Re-review after any prompt or model change.

---

# v4 to v10: claim verifier, 50-document corpus (2026-10-08)

## What changed

| Version | Change | What the review found |
|---|---|---|
| v4 | Corpus grows to 50 pages. Added a **claim verifier**: a second greedy model pass returns `{id, quote, verdict}` for each sentence. Code checks that the quote is really in that passage and runs a contradiction guard. Unsupported sentences are removed; partly supported ones are shown with ◐. | a08 "early symptoms" was still marked supported, because the guard looked for "later" anywhere in the quote. A false "not mentioned" gap sentence was exempt from checking. A compound sentence ("X, whereas Y") was vouched for by one passage. Many true claims were removed because the model's quote wasn't verbatim. |
| v5 | The guard checks only the clauses of the quote that the claim relies on. Fuzzy quote matching. The quote is searched in all supplied passages, and the citation re-pointed if found elsewhere. Compound sentences are split. Hedge check: a claim can't drop "most/may/can" from its source. Gap statements are verified against the rest of the answer. | "can't" matched the hedge pattern (bug). After a wrong sentence was removed, a08 read badly. |
| v6 | One **revision round**: rejected claims, plus what the source actually says, go back to the model, and the rewrite is re-verified. The better-scoring version is kept. | Quotation marks inside claims were never checked, so a10 '"thin corneas"' (not in the passage) got through. a02 cited the wrong passage for a verbatim quote. Claims hidden inside gap sentences went unchecked. The run took 70 minutes. |
| v7 | Quoted text is checked deterministically and the citation set to the passage that contains it. Quotes stitched from several sentences are matched sentence by sentence. Clauses inside gap sentences are verified. The verifier reuses a **KV cache** of the shared prompt prefix; outputs were identical to the uncached path. | A sentence starting with a citation ("[id] describes…") wasn't split from the one before. The revision scoring let a rewrite with zero checkable claims win. |
| v8 | Citations used as a sentence subject become "the source…". Trailing citations stay with their own sentence. New scoring: verified content counts for, unsupported content heavily against. | Any sentence containing "general education" skipped checking. "Disqualify" overstated "raises your risk". |
| v9 | The disclaimer exemption applies to short sentences only. Added a "disqualify vs risk" conflict rule. 8 **fresh questions** added. | a10 "Thin corneas are specifically mentioned" passed at exactly the overlap threshold. f02 "up to 2 weeks" reversed the source's "2 weeks or more". f01 omitted who AREDS 2 is for. |
| **v10** | Low-overlap claims trigger our own search for the best 1–3-sentence window: kept as ◐ only if it overlaps ≥ 0.5, otherwise removed. Range-bound rule ("up to" vs "or more"). Gap statements must refer to the sources. **Intro-chunk swap** in retrieval (F9). **Source caveats**: qualifier sentences from the cited pages, shown verbatim when the answer omits them. The disclaimer is enforced in code. | See below. |

Speed: v7–v10 take about 25–30 seconds per question, including the draft, verification, an optional rewrite and re-verification. v6's 70 minutes was before the KV cache, and that run also used buffered output, so its time can't be broken down.

## v10: claim-level review (10 review + 8 fresh questions)

Every displayed claim was checked by hand against the passage it cites.

| ID | Claims shown | Correct | ◐ flagged correctly | Unflagged overreach | Wrong | Notes |
|---|---|---|---|---|---|---|
| a01 | 1 | 1 | 0 | 0 | 0 | "Early Symptoms: None". The false gap statement was removed. Short, but correct. |
| a02 | 3 | 3 | 0 | 0 | 0 | Both sources quoted verbatim, each cited to the right page (042 = medicines, 043 = surgery). |
| a03 | 1 | 0 | 1 | 0 | 0 | Dropped "most" → ◐ with the source wording. Caveat shows "ask your doctor how often you need an exam". |
| a04 | 5 | 5 | 0 | 0 | 0 | Safety notice comes first, then "go to your eye doctor or the emergency room right away" [014_01]. |
| a05 | 5 | 4 | 0 | **1** | 0 | "often harmless" stretches "often don't need treatment". The emergency exception is present and correctly cited. |
| a06 | 8 | 8 | 0 | 0 | 0 | Injection procedure, frequency ("less often over time" [037_02]) and PDT "much less common" are all exact. |
| a07 | 3 | 3 | 0 | 0 | 0 | Mechanism and symptoms of each condition, each cited to its own page. |
| a08 | 5 | 5 | 0 | 0 | 0 | "later symptoms" is now correct. Macular edema given as an alternative, with its diagnosis and treatment. |
| a09 | (gap) | n/a | n/a | n/a | 0 | No evidence: states the gap only. |
| a10 | 1 | 1 | 0 | 0 | 0 | Keratoconus raises the complication risk [049_02]. Gap statements are true. |
| f01 | 4 | 3 | 0 | **1** | 0 | Vitamin list and beta-carotene correct. "recommended for macular degeneration" lacks the stage qualifier, but **source caveats show it verbatim**: "If you have intermediate AMD…" [031_01]. |
| f02 | 4 | 4 | 0 | 0 | 0 | Viral and bacterial durations exact. **The source conflict with nei_008 ("7 to 10 days") isn't shown**, because nei_008 wasn't retrieved (retrieval F10). |
| f03 | 9 | 8 | 0 | **1** | 0 | "safe and effective": "effective" paraphrases "corrects vision problems". The disclaimer was appended by code. |
| f04 | 4 | 4 | 0 | 0 | 0 | Side effects, "rarely permanent" and other risks all exact. |
| f05 | 2 | 2 | 0 | 0 | 0 | Urgent notice shown (bleach splash). Content is the corneal page's injury guidance. It does **not** say the sources lack chemical first-aid steps. |
| f06 | 6 | 4 | 2 | 0 | 0 | Slit lamp, Schirmer's (5 minutes) and eyelid structure exact. TBUT and "drying too quickly" ◐. |
| f07 | 7 | 4 | 3 | 0 | 0 | ◐ on "advanced" diabetic retinopathy (qualifier dropped) is correct. Flashes, stinging and blurry rest of day exact. |
| f08 | 4 | 1 | 3 | 0 | 0 | "Not always caused by high pressure", normal-pressure glaucoma, neovascular glaucoma: correct, with ◐ where wording is looser. |

**Totals: 72 displayed claims**

| Outcome | Count |
|---|---|
| Correct as stated | 59 |
| Correctly flagged ◐ | 10 |
| Unflagged mild overreach | 3 (4%) |
| **Contradicted or fabricated** | **0** |

For comparison, v3 had 3 contradicted or unsupported claims out of 31, and v4–v9 each had at least one wrong claim that the verifier passed.

## What still isn't solved
1. **Mild paraphrase overreach** ("harmless", "effective"): the 4B verifier calls these SUPPORTED. Fixing this needs a stronger verifier model or stricter extractive answers.
2. **Omissions:** the verifier can't see what an answer leaves out. Source caveats mitigate this by showing qualifier sentences verbatim, but the answer text itself can still be incomplete.
3. **Conflicting sources** only surface if both pages are retrieved (F10).
4. **Over-removal:** some true claims are removed when the model's quote doesn't match. This is the conservative direction.
5. **Gap naming:** f05 didn't say what the sources lack.
6. **Thresholds are hand-set, not learned:** overlap 0.3 / window 0.5, the hedge and conflict rules, and caveat relevance ≥ 2. They were tuned on these 18 questions plus unit cases. **They need a larger, separate test set before being trusted.**

## v11 (2026-10-09): urgent detection and evidence gating, fixed on validation data
Found while running the step 7 validation comparison (`data/results/valid_prefix/`).

**1. `is_urgent()` missed most urgent questions.**
- **Recall:** it caught 10 of the 35 urgent training and validation questions.
- **Cause:** the patterns matched whole words only. "Flashing", "floaters", "hurts", "newborn … discharge", "worse after surgery" and "stuck in my eye" all slipped through.
- **Fix:** the patterns were rebuilt from those 35 questions.
  - Sudden onset plus a symptom; flashes with floaters; many new floaters; a curtain, shade or veil.
  - Injury, chemical or foreign body, each requiring first person.
  - Severe pain, or pain with nausea.
  - Getting worse after surgery or an injection.
  - A newborn with discharge.
- **Result:** recall is now 35/35. Of the other 361 training, validation and tuning questions, 3 are flagged, and all 3 are real emergencies (flashes with a curtain ×2, a bleach splash).
- **Caveat:** the patterns are fitted to these 35 questions, so the frozen test set is the real measure.

**2. Weak-evidence gating withheld urgent guidance.**
- **What happened:** 3 of the 5 urgent validation questions, and 20 of the 30 urgent training questions, had coverage below 0.5, because people describe symptoms in their own words. So `is_weak()` sent "NO USABLE EVIDENCE" even though the right "get help right away" passage was ranked first.
- **Fix:** `retrieve_evidence` no longer treats evidence as weak when `is_urgent(question)` is true.
- **Side effects:**
  - Dry-run prompts for non-urgent questions are byte-identical to before.
  - The step 6 training files are unchanged (md5 `5712fe82…` / `ac720e27…`). The builder had already supplied evidence for urgent examples, so training now matches the app more closely.
  - Remaining mismatch: 7 training and 1 validation premise examples have evidence that the app withholds.

**4. The verifier deleted whole clarify and abstain answers on empty evidence.**
- **What happened:** with no passages, every sentence that wasn't a recognised gap statement was marked unsupported. That included clarifying questions ("Did it start suddenly?"), "I can't tell…", "my sources didn't return passages…" and plain referrals.
- **Effect:** 4 D\* validation answers were reduced to just the disclaimer, and D\* clarify scored 0/8.
- **Fix:**
  - questions to the user, and short referrals without a reason clause, are not treated as claims;
  - the gap regex accepts "didn't/did not … return";
  - "I can't tell…" counts as an individual hedge;
  - exact repeated sentences are dropped (a repetition loop went from 604 words to 52).
- **Content is still checked.** Medical content on empty evidence is still removed: "Please see your doctor, as X can cause Y" is still verified, because the clause after "as" makes a claim.
- **Records:** pre-fix B\*/D\* validation runs are kept in `data/results/valid_prefix_verifier/`.

**5. Curly apostrophes, and answers with nothing left.**
- **Curly apostrophes:** the model writes "didn’t" with a curly apostrophe, which the gap patterns didn't match, so real gap statements were deleted. The verifier now normalises apostrophes first.
- **Nothing left:** if verification removes everything except the disclaimer, `finalize` now shows a fixed sentence: "My sources don't support a reliable answer to this question, so I can't answer it. An eye doctor can help."
- **Records:** round-2 runs are kept as `valid_prefix_verifier/round2_*`.

**3. The urgent notice text was widened** to cover something stuck in the eye, getting worse after surgery or an injection, and newborns with discharge.

## Files
- Questions: `assistant_review_questions.jsonl` (10) and `assistant_fresh_questions.jsonl` (8).
- Logs: `assistant_runs.jsonl` / `assistant_fresh_runs.jsonl` (v10). Earlier versions are kept as `assistant_runs_v*.jsonl`.
- Rendered answers: `assistant_runs_final.txt` and `assistant_fresh_runs_final.txt`.
