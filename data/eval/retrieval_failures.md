# Retrieval evaluation: BM25 v1.1

**Setup**
- Corpus: 30 NEI documents split into 133 chunks (`data/processed/chunks.jsonl`).
- Chunk size: 90–249 words, median 193. 123 of the 133 chunks fall in 150–250. The 10 smaller ones are at the ends of documents.
- Overlap: about 30 words between neighbouring chunks, as whole sentences. It is present in 102 of the 103 neighbouring pairs; it is dropped only where it would push a chunk past 250 words.
- Index: Okapi BM25 (k1=1.5, b=0.75) over title + section headings + passage text.
- Query side: light stemming, plus lay-term expansion at half weight.
- Code: `scripts/retrieval.py`, with evaluation in `scripts/eval_retrieval.py`.

**Note on scores**
- **BM25 `score`** only orders the passages for one question. It is not a probability, it is not comparable across questions, and it doesn't measure whether an answer is medically correct.
- **`coverage`** is the share of the question's own words found in a passage, weighted so rare words count more (IDF). It is a rough on-topic check. `is_weak()` flags a result list when no passage reaches 0.5 coverage.

## Labelling method

Each question stores one or more evidence quotes that I chose by reading the source text, as `{doc_id, quote}`. The evaluation script turns these into `expected_chunk_ids`: every chunk of that document that contains the quote. This keeps the labels correct after re-chunking. If a quote stops matching, the script stops with an error.

**Question sets**

| File | Role | Size |
|---|---|---|
| `retrieval_questions.jsonl` | Main set (the required 20) | 20 |
| `retrieval_heldout.jsonl` | Dev set. It was the first held-out set; its miss (h04) was then used for tuning. | 7 answerable + 1 out of corpus |
| `retrieval_test.jsonl` | Fresh test set. Written before the v1.1 tuning and run once, with no changes afterwards. | 10 answerable + 3 out of corpus |

## Results (v1.1)

| Set | hit@4 | MRR@4 | Answerable questions wrongly flagged weak | Out-of-corpus questions flagged weak |
|---|---|---|---|---|
| Main (20) | **20/20** | 0.754 | 0 | n/a |
| Main, no expansion | 19/20 | 0.700 | 0 | n/a |
| Dev (8) | **7/7** | 0.833 | 0 | 1/1 |
| **Test (13), untuned** | **10/10** | 0.883 | 0 | **2/3** |
| Test, no expansion | 10/10 | 0.883 | 0 | 2/3 |

- **MRR on the main set** dropped from 0.804 in v1 to 0.754, because the chunks changed (promo sections removed, sizes rebalanced). Hit@4 is unchanged.
- **The coverage margin is thin.** The lowest top-passage coverage on an answerable question is 0.51 (t05). Out-of-corpus questions scored 0.00–0.33, plus the 0.58 miss in F7. The 0.5 threshold is a heuristic, not a calibrated cutoff.

Re-run with:

```
.venv/bin/python scripts/eval_retrieval.py
.venv/bin/python scripts/eval_retrieval.py --questions data/eval/retrieval_heldout.jsonl --out data/eval/retrieval_heldout_results.csv
.venv/bin/python scripts/eval_retrieval.py --questions data/eval/retrieval_test.jsonl --out data/eval/retrieval_test_results.csv
# add --no-expand to switch off lay-term expansion; add --show-misses to see the passages returned for each miss
```

## What changed from v1 to v1.1

| Fix | File | Effect |
|---|---|---|
| Remove promo sections ("Healthy Aging Month", "Featured Resource…", "… Resources" link lists). "Did you know?" facts are kept. | `collect_sources.py` | 16 non-content sections removed. "Healthy Aging Month" had repeated a "vision loss … can be prevented" claim across 4 documents. |
| Split list items that contain several paragraphs | `collect_sources.py` | Fixed "surgery If you have symptoms…": the retinal-detachment emergency callout is now its own paragraph. |
| Hard 250-word cap: drop the overlap rather than exceed the cap, and rebalance short final chunks | `retrieval.py` | Max chunk size went from 293 to 249 words, and the count of chunks outside 150–250 went from 15–18 to 10. |
| Evidence-quote labels | `eval_retrieval.py`, question files | Labels survive re-chunking. |
| Lay terms `center/middle → central macula`, `spot → blank blind` | `retrieval.py` | Fixed F5 (h04 now hits). |
| Coverage signal plus `is_weak()` | `retrieval.py` | Flags 3 of 4 out-of-corpus questions, with no false flags on 37 answerable ones. |
| Coverage counts a lay term as present when its translation is | `retrieval.py` | Fixed a false "weak" flag on q15 ("dangerous" never appears in the corpus). |

## Failure log

### F1. q12 "nearsighted vs farsighted": stemming gap (fixed in v1; rank still weak)
- **Cause:** "nearsighted" didn't match "nearsightedness", so "difference" pulled in color-blindness chunks.
- **Fix:** strip `-ness`. The question now hits at rank 4.
- **Still open:** comparison questions need retrieval per entity, then a merge.

### F2. q06 "shots in the eye": terminology gap (fixed)
- **Cause:** the corpus says "injects" or "anti-VEGF".
- **Fix:** expansion `shot → inject injection`. The question hits at rank 2.

### F3. q04 "can lost vision be **restored**": negation phrased differently (improved to rank 2)
- **Cause:** the corpus says "won't **undo**" and "no **cure**".
- **Fix:** expansion `restor → undo reverse cure`.
- **Watch item:** this is a "no" answer. The generation step should be tested so it never implies vision can be restored.

### F4. q20 "is uveitis serious": wording gap (improved to rank 2)
- **Cause:** the corpus says "vision loss… right away" rather than "serious".
- **Fix:** expansion `serious → vision loss blindness emergency right away`.

### F5. h04 "dark spot in the center of my vision": misleading word overlap (fixed in v1.1, on the dev set)
- **v1 result:** "dark spots" pulled in floaters, retinal detachment and vitreous detachment.
- **Fix:** expansions `center/middle → central macula` and `spot → blank blind`. The AMD and macular-hole evidence is now in the top 4.
- **Caveat:** these terms were tuned on this question, which is why h04 now counts as dev, not test.
- **Remaining risk:** floaters chunks still rank alongside the right ones. The model should say the symptom fits several conditions and recommend an exam rather than pick one.

### F6. Out-of-corpus questions return passages anyway (mitigated)
- **Before:** BM25 always returns something. "Sitting too close to the TV" returned four unrelated chunks, and no BM25 score cutoff separated them from real hits.
- **Fix:** the `coverage` check plus `is_weak()`.
  - Flagged correctly: TV (0.28), solar eclipse (0.33), keratoconus (0.00).
- **Next step:** when `is_weak()` is true, the generator should say the sources don't cover the question.

### F7. t13 "Can I get LASIK if I have thin corneas?": partially in corpus (open, found on the untuned test set)
- **Result:** not flagged (coverage 0.58). The top passages were tears, blepharitis and corneal-conditions chunks, none of which answer it.
- **Cause:** "cornea" and related words are common in the corpus, so word overlap looks on-topic. The real gap is the specific question: who is a candidate for LASIK.
- **Implication:** coverage can catch questions that are fully off-topic, not questions whose topic is covered but whose specific question is not. Only a model, or reranking, that checks whether a passage actually answers the question can catch this. It needs a dedicated test in the generation evaluation.

### F8. Mixing up conditions (watch item, not a retrieval miss)
- **Example:** for q05 "vitamins for macular degeneration", the retinitis pigmentosa passage about vitamin A also appears in the top 4.
- **Implication:** prompts should require the model to say which condition each piece of evidence comes from.

## Recommendation / exception splits (re-checked on v1.1 chunks)

| Case | Recommendation | Exception | Retrieved together? |
|---|---|---|---|
| Exam frequency (q07) | Every 1–2 years if you're at risk | Diabetes or high blood pressure: at least once a year | Yes. Both sentences are in the same chunk, and the overlap repeats them in the next one. |
| Floaters (q15) | Usually harmless | Sudden new floaters with flashes: go right away | Yes. Both chunks are in the top 4. |
| AMD supplements (q05) | May slow AMD | Only for intermediate AMD, or late AMD in one eye | Yes, in the same sentence. |
| Macular pucker (h05) | Most need no treatment | Surgery if symptoms are bad | Yes, in the same chunk. |
| High eye pressure (t10) | High pressure is a risk factor | Not everyone with high pressure gets glaucoma; normal-pressure glaucoma exists | Yes, at rank 1. |

## Still open
- Comparison questions (F1) and specific questions about a covered topic (F7).
- The 0.5 coverage threshold has little margin. Re-check it whenever the corpus grows; the 30→60 expansion will shift IDF weights.
- Imaging content (OCT, angiography) is still missing from the corpus.

## v1.2: corpus expanded to 50 documents (2026-10-08)

The 20 added pages are NEI subpages from `nei_expansion_candidates.csv`. They cover AREDS 2, wet AMD treatments, cataract surgery, causes and types, the eye, diabetic retinopathy injections and laser, dry eye causes and testing, glaucoma pressure, medicines, surgery and types, pink eye causes, treatment and newborns, types of refractive errors, refractive surgery, and retinal detachment types. All 20 are `public_domain_verified`. The corpus now has 196 chunks, with a maximum of 250 words.

**Relabeling.** New pages answer many existing questions, sometimes better than the original 30. I added evidence quotes for those, each checked by reading the passage text, so a label covers every passage that answers the question. Two "out-of-corpus" test items stopped being out of corpus:

| Question | Before | Now |
|---|---|---|
| t12 "What is keratoconus?" | out of corpus | nei_049 defines it ("a disease that makes the cornea thinner over time") |
| t13 "LASIK with thin corneas?" | out of corpus (F7) | nei_049 covers LASIK candidacy: "LASIK isn't right for everyone", keratoconus raises the risk, and a dilated exam is needed |

**Results after relabeling**

| Set | hit@4 | MRR@4 | Out of corpus flagged weak |
|---|---|---|---|
| Main (20) | 20/20 | 0.842 | n/a |
| Main, no expansion | 20/20 | 0.796 | n/a |
| Dev (8) | 7/7 | 0.810 | 1/1 (TV) |
| Test (13) | 12/12 | 0.903 | 1/1 (eclipse) |

No answerable question was wrongly flagged weak.

### F9. q05 "vitamins for macular degeneration": exception split across chunks (mitigated in the assistant)
- **What happens:** at 50 documents, the AREDS 2 "ingredients" chunk (nei_031_chunk_03) ranks first. The eligibility qualifier is in nei_031_chunk_01, which is not in the top 4. That qualifier says the supplements are for intermediate AMD or late AMD in one eye, and can't stop early AMD from progressing.
- **Effect:** an answer built only from the top 4 lists the vitamins but not who they are for.
- **Mitigation:** in `assistant.retrieve_evidence`, when a page supplies two or more passages but not its first chunk, chunk_01 replaces that page's lowest-ranked passage. Still 4 passages in total. The raw `retrieve()` used in these retrieval scores is unchanged.

### F10. "How long does pink eye last?": source conflict not retrieved (open)
- **The conflict:** nei_008 (updated 2025-11-05) says pink eye "often gets better on its own after 7 to 10 days". nei_046 (updated 2019-06-26) says viral pink eye "usually gets better in 1 to 2 weeks… sometimes 3 weeks or more", and bacterial pink eye takes "2 to 5 days… 2 weeks or more".
- **What happens:** for this wording, the top 4 holds the two nei_046 chunks plus two dry-eye chunks, which match "how long… lasts". nei_008 doesn't appear, so the assistant can't show the conflict.
- **Status:** the prompt tells the model to present disagreeing sources with their dates, but that only works when both are retrieved. Possible fixes: per-topic diversification, or always retrieving the main condition page. Not tuned here.
