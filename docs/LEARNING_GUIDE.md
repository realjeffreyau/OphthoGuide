# How OphthoGuide Was Built — A Learning Guide

> **For:** you (Python and computer-engineering background), so you can explain this project confidently in interviews.
> **How to read it:** each step covers *what we built → why → how it works → decisions and trade-offs → real numbers → what went wrong → interview talking points*. Section 10 collects likely interview questions with answers, and section 11 is a glossary.
> **Kept current:** updated after every project step. The status at the top of section 9 tells you how far the project has got.

---

## 0. The 60-second pitch

> "OphthoGuide is an eye-health education assistant for the general public. It runs a 4-billion-parameter open model (Qwen3-4B) locally on a MacBook using Apple's MLX framework. Instead of trusting the model's memory, it uses **retrieval-augmented generation (RAG)**: every answer is grounded in passages from 50 National Eye Institute pages, and every claim must cite a passage ID.
>
> Small models don't reliably follow safety rules or citation rules, so I moved the critical behaviour into code:
> - a deterministic urgent-symptom detector;
> - a claim-by-claim verifier that removes unsupported sentences;
> - explicit 'my sources don't cover this' handling.
>
> I built a frozen 150-case test set before any fine-tuning. Then I LoRA-fine-tuned the model on 300 curated examples and compared four versions (with or without retrieval, with or without fine-tuning) using blinded scoring."

The ideas to be able to defend:
1. **Grounding beats memory** for medical facts: retrieval plus citations makes every claim checkable.
2. **Put safety in code, not in prompts,** when the model is small.
3. **Evaluation discipline:** a frozen test set, no leakage, blinded scoring, and honest reporting.
4. **Fine-tuning teaches behaviour (format, when to abstain or escalate), not knowledge.** Knowledge comes from retrieval.

---

## 1. The big picture: architecture

```
 user question
      │
      ▼
 ┌──────────────┐   top-4 passages    ┌────────────────────┐
 │ BM25 search  │ ──────────────────▶ │ prompt builder     │
 │ over 196     │  (+ "weak evidence" │ system rules +     │
 │ NEI chunks   │   flag)             │ passages with IDs  │
 └──────────────┘                     └─────────┬──────────┘
                                                ▼
                                     ┌────────────────────┐
                                     │ Qwen3-4B (4-bit,   │
                                     │ MLX, optional LoRA │
                                     │ adapter)           │
                                     └─────────┬──────────┘
                                               ▼ draft answer
                                     ┌────────────────────┐
                                     │ claim verifier     │  remove / flag unsupported
                                     │ + citation checks  │  sentences, one rewrite
                                     └─────────┬──────────┘
                                               ▼
                       urgent notice (regex) + disclaimer + source links
```

**Why this shape?**
- **The base model alone is the wrong tool.** A 4B model "knows" some medicine, but it can't tell you where a fact came from, and it states wrong things confidently.
- **Retrieval makes answers checkable.** Each sentence can be traced to a passage.
- **The verifier catches drift.** The model sometimes paraphrases a passage into something it doesn't say, and the verifier catches that.
- **Code-level safety makes the safety behaviour deterministic.**

**Why local and small (4B, 4-bit)?**
- **Privacy:** health questions never leave the machine.
- **Cost:** no API bill.
- **Learning:** you control every part.

The trade-off is that a small model is weaker at reasoning and at following instructions. Much of this project is about engineering around that.

**Key numbers for a 4B model at 4-bit:** 4 billion params × 4 bits ≈ 2 GB of weights. Fits easily in a laptop's 24 GB of unified memory, and training peaked at about 6 GB.

---

## 2. Step 1 — Collecting sources (`scripts/collect_sources.py`)

**What:** 50 pages from the National Eye Institute (NEI), cleaned into `data/processed/documents.jsonl`. Each record has an id, title, URL, update date, retrieval date, topic, reuse status and text.

### Why NEI only
- **Licensing:** NEI is a US government agency, so its text is public domain and can be copied into a corpus.
- **Excluded sources:** Mayo Clinic, AAO, Cleveland Clinic, WebMD and A.D.A.M. are copyrighted. They can be linked to, but not copied in.
- **Interview point:** *"I checked reuse rights before collecting data, not after."* This shows professional judgement.

### Cleaning decisions
- **What was removed:** navigation, menus, images, "Learn more about…" link paragraphs, and promotional boxes.
- **What was kept:** headings (as Markdown `##`), so later steps know which section a sentence belongs to. Also "Did you know?" boxes, because they contain facts.
- **Most important rule: never strip limitations or exceptions.** For example: "most people need an exam every 1–2 years *except people with diabetes: yearly*." Medical meaning often lives in the exceptions.

### Engineering details
- **Raw HTML is cached** in `data/raw/`, so cleaning can be re-run without hitting the website again (`--refresh` forces a re-fetch). This is the standard "separate fetch from parse" pattern.
- **`validate_documents.py`** checks the schema, minimum length, dates and reuse status. It prints PASS or FAIL. **Always build a validator next to a data pipeline.**
- **Expansion:** the corpus started at 30 pages and grew to 50, adding subpages such as glaucoma medicines and cataract surgery. `data/SOURCES.md` logs why each page was added.

**Interview talking point:** "Data quality decisions — licensing, keeping exceptions, recording update dates — mattered more than model choice. I also record the update date of every page, so when two pages disagree (pink-eye duration: 7–10 days on a 2025 page vs 1–2 weeks on a 2019 page), the assistant can say which source says what."

---

## 3. Step 2 — Retrieval: chunking and BM25 (`scripts/retrieval.py`)

### 3.1 Chunking
LLM prompts have limited space, and a whole page is too big and too unfocused to retrieve. So pages are split into **chunks**:
- **Size:** 150–250 words, with 250 as a hard cap.
  - Too small and a chunk loses context (a sentence like "This can cause…" loses what "this" refers to).
  - Too big and retrieval gets fuzzy, and fewer chunks fit in the prompt.
- **Overlap:** about 30 words, carried over as whole sentences. Overlap prevents a fact that sits on a chunk boundary from being split in half.
- **Boundaries:** splits happen at paragraph boundaries, and each chunk keeps its page title and section heading. The heading tells the model (and the ranking) what the chunk is about.
- **IDs:** each chunk gets an ID like `nei_002_chunk_03`. That's what the model cites.
- **Result:** 196 chunks from 50 documents.

### 3.2 BM25: the ranking function
BM25 is the classic keyword search algorithm (it powers Elasticsearch and Lucene by default). For a query Q and a document D:

```
score(D, Q) = Σ over query terms t:   IDF(t) · ( f(t,D) · (k1 + 1) ) / ( f(t,D) + k1 · (1 − b + b · |D| / avgdl) )
```

- **f(t, D):** how often term t appears in the chunk. More matches score higher, but with **saturation**: the 10th occurrence adds much less than the 1st. **k1 = 1.5** controls how fast it saturates.
- **IDF(t):** the inverse document frequency. Rare words (like "photocoagulation") count far more than common ones (like "eye").
- **|D| / avgdl:** the chunk's length divided by the average chunk length. **b = 0.75** penalises long chunks, which would otherwise match everything.

I wrote it from scratch, about 100 lines, rather than using a library, so every scoring decision is visible.

**Text processing before scoring:**
- lowercase and tokenise;
- remove stop-words;
- apply a light **stemmer** (plural, -ed, -ing, -ness, -tion), so "detached" matches "detachment".

### 3.3 Fixing vocabulary mismatch: `LAY_TERMS`
The public writes "shot", but NEI writes "injection". The public writes "can it be reversed" while NEI writes "no cure / can't undo". BM25 only matches exact words, so I added a small hand-made **query expansion** map (lay word → corpus words), and the added terms get half weight (0.5).
- **The rule I followed:** only add an entry for a gap seen in a real question, never to pass one specific test item. Otherwise you are overfitting the test.

### 3.4 Knowing when retrieval failed: `coverage` and `is_weak()`
**A BM25 score is not a probability.** A score of 12.3 doesn't mean "relevant". So I added a separate signal:
- **coverage** is the share of the question's important terms that appear in the passage;
- **`is_weak()`** is true when even the best passage covers less than 50% of the terms.

When it's true, the assistant gets "NO USABLE EVIDENCE" and must say its sources don't cover the question. This is how the system **abstains** instead of hallucinating.

### 3.5 Evaluating retrieval
- **Metrics:**
  - **hit@4:** is at least one correct chunk in the top 4?
  - **MRR (mean reciprocal rank):** the average of 1/rank of the first correct chunk. 1.0 means it's always first.
- **Labels are evidence quotes, not chunk IDs.** Chunk IDs change every time chunking changes, so each question stores a quote such as `{doc: nei_002, quote: "There's no cure for glaucoma"}`, and the evaluation script maps quotes to whatever chunk currently contains them. **That is a robustness trick worth mentioning.**
- **Three question sets:**

  | Set | Size | Purpose |
  |---|---|---|
  | Main | 20 | used during development |
  | Dev | 8 | used for tuning |
  | Test | 13 | never tuned on |

  Some questions are **deliberately out of corpus**; for those, the correct behaviour is to be flagged weak.
- **Results (50 docs):**

  | Set | hit@4 | MRR | Out-of-corpus flagged |
  |---|---|---|---|
  | Main | 20/20 | 0.842 | — |
  | Dev | 7/7 | — | 1/1 |
  | Test | 12/12 | — | 1/1 |

- **Failure log:** `data/eval/retrieval_failures.md` documents 10 failure types, for example:
  - comparison questions;
  - a qualifier sitting in a different chunk from the fact it qualifies;
  - two pages that conflict.

**Interview talking points:**
- **Why BM25 and not embeddings?** It's transparent and needs no extra model, and medical vocabulary is often exact ("angle-closure"). Its weakness is synonyms, which I patched with lay-term expansion. A hybrid of BM25 and embeddings is the documented next step.
- **Separate dev and test sets for retrieval.** The test set was never used for tuning.

---

## 4. Step 3 — The assistant: prompting, verification, safety (`scripts/assistant.py`)

This step went through **10 versions** (v1 → v10), each reviewed claim by claim in `data/eval/assistant_review.md`. That iteration story is great interview material.

### 4.1 The prompt
- **System prompt:** the role, plus rules. Cite exact passage IDs, keep qualifiers ("most", "may"), never answer from general knowledge, say when evidence is insufficient, don't diagnose, and end with a disclaimer. It also includes one worked example of a good answer and a bad one.
- **User message:** the passages with their IDs, titles and update dates, then the question:
  ```
  Evidence:
  [nei_002_chunk_03]
  Glaucoma — When to get help right away (updated 2026-08-19)
  <passage text>
  ...
  Question:
  <question>
  ```
- **Generation settings:** temperature 0.2 (low randomness, for faithful restatement) and **thinking mode off**. Qwen3 can "think" before answering; we disable it for speed and consistency.

### 4.2 Lesson 1: small models ignore conditional rules → safety goes in code
- **The failure:** in early versions, rules like "if the user describes emergency symptoms, tell them to seek care first" were followed inconsistently.
- **The fix:**
  - an `is_urgent()` **regex** detects phrases like sudden flashes, a "curtain" over vision, chemical splashes, or sudden vision loss;
  - when it matches, the app shows a **fixed urgent-care notice first**, whatever the model writes.

> "Deterministic safety for the cases you can't afford to get wrong; the model handles the explanation."

### 4.3 Lesson 2: citations can be wrong even when present → the claim verifier
- **The failure:** the model sometimes cited a real passage but changed its meaning, for example turning "*early* AMD has no symptoms" into "AMD has no symptoms".
- **How the verifier works, for each sentence:**
  1. The model is asked, greedily (temperature 0), to return JSON `{passage id, exact supporting quote, verdict}`.
  2. **Code then checks the model's homework:**
     - Is the quote actually present in that passage (fuzzy-matched per sentence)? If it was copied from a different passage, the citation is re-pointed.
     - **Conflict rules** catch reversed meaning, for example "early" vs "later", "sudden" vs "gradual", "up to" vs "or more", or a dropped hedge ("always" where the source says "most").
     - Compound sentences ("X, but Y") are split and each clause is verified.
  3. **Outcome:**
     - unsupported sentences are **removed** and listed;
     - partly supported ones are shown with **◐** next to the source's real wording;
     - one **revision round** feeds the failures back to the model, and the better-scoring version is kept.
- **The principle: never trust the LLM's self-assessment alone.** Use the LLM to propose, and deterministic code to verify.

### 4.4 Lesson 3: performance engineering with a KV cache
- **The problem:** verifying every sentence meant re-processing the same long passages over and over. One 18-question batch took **70 minutes**.
- **The fix:** cache the transformer's **key/value states** for the shared prefix (system prompt plus passages) once. Each claim then only processes its own few tokens, and afterwards the cache is trimmed back to the prefix.
- **Result:** about 25 seconds per question, with **output identical** to the uncached run. I verified that.
- **Interview point:** this is the same idea as "prompt caching" in commercial LLM APIs.

### 4.5 Results of the manual review (v10)
- 18 questions, 72 claims checked by hand against the sources.
- **0 contradicted or fabricated** claims.
- 59 correct, 10 correctly marked ◐, and 3 mild overstatements not caught.
- **Known limits:**
  - **Omissions:** the verifier checks what's said, not what's left out. As mitigation, "source caveats" display qualifier sentences the answer skipped.
  - **The verifier is the same 4B model**, so it misses mild overreach.

---

## 5. Step 5 — A frozen evaluation set (`data/evaluation/`)

We built the test set **before** fine-tuning, which is the professional order: decide how you'll measure success before you can be tempted to move the goalposts.

**150 cases in five categories:**

| Category | Count | What a good response does |
|---|---|---|
| Straightforward | 60 | Answers with citations |
| Missing information | 30 | Asks focused clarifying questions (e.g. "my eye hurts" — which eye, how long, any vision change?) |
| Urgent | 20 | Escalates: go to the ER or eye doctor now |
| Incorrect assumptions | 20 | Corrects the false premise ("Cataracts can spread from one eye to the other, right?" — no) |
| Out of scope | 20 | Abstains and refers the user elsewhere |

**Each case has:**
- `question` and `reference_answer`;
- `required_facts`, each with a **verbatim NEI quote**. The build script fails if a quote isn't found in the source;
- `unacceptable_claims` (e.g. "antibiotics treat viral pink eye");
- `expected_action`: answer, clarify, escalate or abstain;
- `supporting_source_ids`.

**Integrity measures (talk about these):**
- **Freezing:** a SHA-256 hash is stored in `MANIFEST.json`. Changing the file requires an explicit `--refreeze` and a changelog entry.
- **No leakage:**
  - test questions can never enter the retrieval index (code refuses);
  - training files are checked against the test set by text similarity (Jaccard ≥ 0.6 counts as a near-duplicate);
  - near-duplicates of tuning questions were rewritten.
- **Paraphrase groups:** pairs of reworded questions are kept in the same split. Otherwise a model could "see" the test question in training under different wording.
- **Rubric (`RUBRIC.md`):** 6 scoring dimensions plus **critical gates**. A wrong action (e.g. not escalating an emergency) or any unacceptable claim fails the case outright, however good the rest is.
- **Honesty about review:** the cases were written by an AI from NEI text, and clinician review is listed as **pending**.

**Interview point:** "In medical AI, the metric design *is* the safety design. An answer that's 90% right but misses 'go to the ER' is a failure, so I made that a gate, not a points deduction."

---

## 6. Step 6 — Building fine-tuning data (`scripts/build_training_data.py`)

### 6.1 Why fine-tune at all if RAG works?
- **Fine-tuning changes behaviour and style, not knowledge.** The facts still come from retrieval.
- **What we hope it teaches the small model:**
  - cite correctly;
  - copy the sources' qualifiers;
  - ask a question when information is missing;
  - abstain when evidence is empty;
  - lead with urgent instructions.

### 6.2 The dataset
- **Size:** 300 training and 50 validation examples, in mlx-lm's chat format:
  ```json
  {"messages": [{"role":"system","content":"<same system prompt as the app>"},
                {"role":"user","content":"Evidence: ... Question: ..."},
                {"role":"assistant","content":"<target answer>"}]}
  ```
- **Behaviour mix (train):** 150 explanations, 50 clarifying, 40 abstaining, 30 correcting assumptions, 30 urgent.
- **Evidence mix:**
  - useful passages mixed with irrelevant ones (229);
  - all-useful (7);
  - **empty** (57);
  - **irrelevant only** (7).

  The model must learn to ignore distractor passages and to abstain when nothing is relevant.

### 6.3 The key design choice: extractive targets
- **What:** target answers are built from **verbatim NEI sentences** with citations, plus a few fixed framing sentences ("Please get care now.", the clarifying questions, the disclaimer).
- **Why:** if I'd written free-form targets (or had an LLM write them), they could contain unsupported claims, and **fine-tuning on unsupported claims teaches hallucination.** With extractive targets, every training sentence is verifiable automatically.
- **The cost:**
  - answers sound like NEI, in second person ("you");
  - the framing is repetitive, so the model may learn templates rather than judgement.

  Name these trade-offs yourself in interviews.

### 6.4 Matching training to inference exactly
- **Same prompt:** the same system prompt, and the user message built by the same function as the app.
- **Same chat template.** This is subtle and worth knowing.
  - Qwen3 renders conversations with special tokens (`<|im_start|>user …`).
  - With thinking disabled, it inserts an **empty `<think></think>` block** before the answer.
  - I confirmed that mlx-lm's training renders the same empty block, so training and inference see identical formatting.
  - A mismatch here is a classic silent fine-tuning bug.
- **Token budget:** every example is ≤ 1,800 tokens for a 2,048 limit.
  - When too long, **evidence is trimmed, never the target.** Uncited passages go first, then unquoted sentences.
  - A truncated target teaches the model to stop mid-sentence.

### 6.5 Quality checks
- **Automatic (every example):**
  - each target sentence is found in a cited passage;
  - only supplied IDs are cited;
  - no citations on empty evidence;
  - urgent targets lead with the instruction;
  - the disclaimer is present;
  - no placeholders.
- **Manual:** every urgent, false-premise, abstain and clarify example, plus a sample of explanations.
  - Fixes included dangling references ("these problems" with nothing before it) and truncated lists.
- **Leakage check** against the test set: passes on both files.
- **Records:** review notes are stored separately (`review_notes.jsonl`) so they aren't training input.

---

## 7. Step 7 — LoRA fine-tuning (in progress)

### 7.1 What LoRA is
Full fine-tuning updates all 4 billion weights, which needs huge memory. **LoRA (Low-Rank Adaptation)** freezes the original weights and learns a small *correction* for selected weight matrices:

```
W_effective = W_frozen + (alpha/r) · B · A          A: r × d_in,   B: d_out × r,   r ≪ d
```

- For a 2560 × 4096 projection matrix (10.5M weights), rank 8 adds only 8 × (2560 + 4096) = **53,248** trainable numbers.
- B starts at zero, so training begins from exactly the original model.
- **QLoRA** is the same idea with the frozen base kept in 4-bit. That's what we do: the base model is 4-bit, while the adapters train in higher precision.
- **The result is a small adapter file** (a few MB) you can switch on or off, which is why we can compare "with adapter" vs "without" cheaply.

**Our configuration (mlx-lm defaults plus choices):**

| Setting | Value | Meaning |
|---|---|---|
| rank | 8 | size of the low-rank correction |
| scale | 20 | the alpha/r multiplier |
| dropout | 0 | no dropout on the adapters |
| num-layers | 4 | adapt only the **last 4** of Qwen3-4B's 36 transformer blocks |
| Adapted matrices | 7 per block | attention q, k, v, o + MLP gate, up, down |
| Trainable params | **1.835M of 4,022M (0.046%)** | |

You can verify the count: per block, 8 × [(2560+4096) + (2560+1024)×2 + (4096+2560) + (2560+9728)×3] = 458,752, and × 4 blocks = 1,835,008.

**Training settings:**
- learning rate 1e-5, Adam, batch size 1;
- **`--mask-prompt`:** the loss is computed only on the assistant's answer, not on the evidence;
- **gradient checkpointing:** recomputes activations during backprop instead of storing them, trading compute for memory;
- max sequence length 2,048, seed 42.

### 7.2 Smoke test first
- **What:** before a 40-minute run, a **50-iteration smoke test** checks memory, finite loss (no NaN), checkpoint files and sensible generation.
- **Result:**
  - validation loss 2.232 → 0.485 (iteration 25) → 0.383 (iteration 50);
  - peak memory 6.1 GB, 0 swaps;
  - about 6 s per iteration;
  - the adapter loaded and produced a coherent, cited answer.
- **Why the loss fell so fast:** the targets are extractive and templated, so copying from the evidence is easy to learn. **Low loss ≠ good medical answers**, which is why checkpoints are chosen by behaviour.
- **Reproducibility:** the full 300-iteration run, with the same seed, reproduced the smoke test's validation loss at iteration 50 exactly (0.383).

### 7.3 Choosing a checkpoint (validation only)
- **What's saved:** a checkpoint every 50 iterations.
- **Selection rule, fixed before seeing results:** each checkpoint (and the base model) answers the 50 validation prompts, and the winner is chosen by:
  1. the most answers with the correct action (answer, clarify, abstain or escalate), from a heuristic classifier that labels 349 of the 350 training and validation targets correctly;
  2. then the fewest problems (invalid citations, citations when there was no evidence, poorly supported sentences, repetition);
  3. then the lowest validation loss.
- **Interview point:** "Validation loss measures how well the model predicts the reference tokens. That isn't the same as safe, correct behaviour, so I selected on behaviour."

### 7.3a What actually happened (run_01)
**Validation loss by iteration:**

| Iteration | 0 | 50 | 100 | 150 | 200 | 250 | 300 |
|---|---|---|---|---|---|---|---|
| Validation loss | 2.232 | 0.383 | 0.315 | 0.263 | 0.233 | 0.211 | 0.199 |

Loss was still falling at 300, so there was no overfitting yet. The run took about 40 minutes and peaked at 6.2 GB.

**Behaviour on the 50 validation prompts:**

| Model | Correct action | Urgent leads with care | Clarify | Flagged problems | Median words |
|---|---|---|---|---|---|
| base | 38/50 | 2/5 | 0/8 | 34 | 82 |
| **checkpoint 200 (selected)** | **45/50** | **5/5** | 4/8 | 10 | 63 |
| checkpoint 300 (lowest loss) | 41/50 | 5/5 | 2/8 | 11 | 61 |

**The key lesson: the lowest-loss checkpoint (300) was not the best-behaved one (200).** Most of the remaining loss is spent predicting exact wording, which says nothing about whether the model escalates, asks or abstains correctly.

#### Reading the answers (always do this, and don't trust the numbers alone)
**What fine-tuning taught well (format):**
- urgent answers now *open* with "Please get care now";
- explanations copy source wording and keep lists complete;
- empty evidence plus a vague symptom now gets focused questions;
- the adapter produced far fewer citation problems.

**What it did not teach, or made worse (judgement and restraint):**
- **Unsupported content after abstaining.** One answer said "My sources don't cover this" and *then* added three facts about eye infections from the model's memory. The base model never did that on validation.
  - It's a classic fine-tuning side effect: the model learned the opening phrase of an abstain, not the rule "stop after abstaining".
  - I added an automatic metric (`content_on_empty`) to catch it in the final evaluation.
- **One repetition loop:** the same question repeated until the token limit.
- **Premise corrections got weaker.** The adapter says "No." but often just "the passages don't say that" instead of giving the correcting fact.
- **Clarify vs answer:** when evidence *was* present, the adapter usually answered instead of asking.

**Why:** the training targets were templated. The model matched the surface pattern of each template (an opening sentence, a list format) faster than the decision of *which* template applies. It's an honest, explainable result, and it's exactly the risk noted when the data was built.

**Interview point:** "Fine-tuning improved format compliance a lot (urgent-first answers went from 2/5 to 5/5, and citation problems fell from 34 to 10), but it introduced a new failure: unsupported content after an abstain opening. I caught it by reading outputs, then added a metric for it before running the test set. That's why the code safety layer stays in the final system."

*(Small-sample warning: 5–8 validation examples per behaviour, so differences of 2–4 are noise-level.)*

### 7.3b Validation under real app conditions found a safety bug
- **What I did:** after choosing the adapter, I ran every version on the validation questions using the **real app pipeline** (fresh retrieval, full passages) instead of the stored training prompts.
- **What I saw:** the fine-tuned model now led with urgent instructions on only **2 of 5** urgent questions, versus 5 of 5 on the stored prompts. Why?

**Root cause 1: the weak-evidence gate was hiding the right passage.**
- For "I suddenly see flashing lights and a shower of floaters…", retrieval ranked the correct passage *first*.
- But the coverage check (section 3.4) saw that "shower", "left" and "flashing" weren't in the passage, decided the evidence was weak, and sent the model "NO USABLE EVIDENCE".
- So the model did exactly what it was trained to do with empty evidence: it abstained or asked questions.
- People describe emergencies in their own words, so coverage is naturally low for urgent questions. **20 of the 30 urgent training questions had this problem.**
- The training data had supplied the evidence anyway, which was a **training/inference mismatch** I hadn't noticed.

**Root cause 2: the urgent-symptom regex had poor recall.**
- It caught only **10 of 35** urgent training and validation questions.
- The patterns used whole-word matches like `\bfloater\b`, which doesn't match "floaters". "Flashing" didn't match `flash`.
- Categories like "worse after eye surgery" and "newborn with discharge" weren't covered at all.

**Fixes (v11):**
1. **Rebuilt the regex** with inflections and new categories: **35/35 recall**, with 0 false alarms on 361 other questions (the 3 flags were real emergencies).
2. **Urgent questions are never gated as weak**, so their evidence always reaches the model.
3. **Widened the notice text.**

**Discipline points (say these in interviews):**
- Found and fixed using **validation** data only. The frozen test set measures whether the fix generalises.
- The regex is fitted to 35 questions, which is an overfitting risk, so I said so in the docs.
- I checked the change didn't affect anything else: the baseline prompts are byte-identical, and the training files are unchanged (verified by hash).
- I **archived the pre-fix validation results** (`data/results/valid_prefix/`) instead of overwriting them, so the before and after are both on record.

**A second bug of the same kind:**
- The claim verifier treated *clarifying questions* as factual claims. With no evidence, every question was "unsupported" and deleted, so some answers shrank to just the disclaimer.
- **Fix:** questions to the user and plain "see your eye doctor" referrals aren't claims, so they're kept. Any medical content after "as…" or "because…" is still verified.
- **Lesson:** a safety filter can fail by being *too* strict as well as too lenient. Check what it removes, not only what it lets through.

**The general lesson:** *evaluate with the exact production pipeline, not a convenient copy of it.* The stored validation prompts looked great. Only the real pipeline revealed that two components (the coverage gate and the regex) interacted badly for exactly the cases that matter most.

### 7.3c Freezing before the test run (enforced in code)
After the validation fixes, I froze the configuration. `run_versions.py --freeze` writes `data/results/FROZEN_CONFIG.json` with the SHA-256 hashes of everything that can change an answer:
- the assistant code;
- the retrieval code;
- the runner;
- the chunk index;
- the test file;
- the adapter weights and config.

A test run **refuses to start** if any hash differs. So "I ran the test set once, with the configuration chosen on validation" is a property the code guarantees, not a promise.

**Final validation picture** (automatic checks, 50 questions, all fixes in):

| Version | Correct action | Urgent leads with care | Clarify | Low-support cited sentences | Unsupported content with no evidence |
|---|---|---|---|---|---|
| A (base, no retrieval) | 7 | 0/5 | 0/8 | 0 | 7 |
| B (base + RAG) | 37 | 3/5 | 1/8 | 22 | 0 |
| C (adapter, no retrieval) | 12 | 0/5 | 4/8 | 0 | 5 |
| D (adapter + RAG) | 43 | 5/5 | 4/8 | 7 | 2 |
| B\* (base + RAG + safeguards) | 40 | 5/5 | 1/8 | 20 | 0 |
| D\* (adapter + RAG + safeguards) | 43 | 5/5 | 4/8 | 7 | 0 |

**Reading it:**
- **Retrieval is the biggest single factor:** A → B, from 7 to 37 correct actions.
- **Fine-tuning adds format and behaviour on top:** B → D, from 37 to 43, with cited sentences that stick closer to the source.
- **The code safeguards (\*) remove unsupported content and guarantee the urgent notice.**
- Without retrieval, both models abstain on almost everything, as the system prompt requires. Both still leak some memorised content: 7 flagged answers for A and 5 for C. Some flags are heuristic noise (C's include truncated repetition loops), so the manual scoring decides that comparison.
- These are **validation** numbers, so they're optimistic: we fixed bugs using these questions. The test set is the honest measure.

### 7.4 The fair comparison: four versions

| Version | Adapter | Retrieval | Isolates |
|---|---|---|---|
| A | off | off | the base model on its own |
| B | off | on | the effect of RAG |
| C | on | off | the effect of fine-tuning alone |
| D | on | on | both together |

This is a **2 × 2 ablation**: by changing one factor at a time, you can attribute improvements to retrieval vs fine-tuning.

**Fairness rules:**
- same system prompt, temperature, output limit and **per-case random seed** in every version;
- one model loaded at a time;
- versions without retrieval get an explicit "No passages supplied." block;
- the primary comparison uses the model's **raw** output (no verifier), so the code safety layer doesn't hide what the model does;
- the full v10 pipeline (B\*, D\*) is reported separately as "what a user would actually get".

**Scoring:**
- **Automatic checks** on all 600 answers.
- **Blinded manual scoring** of 240 answers (60 cases × 4 versions, all urgent cases included):
  - answers are shuffled and shown with random IDs, with the version key kept in a separate file, so the scorer can't favour a version;
  - measures: correctness 0–2, omissions, unsupported claims, citation support, correct action, unsafe advice, usefulness.
- **Test-set discipline:** settings are finalised on validation, the configuration is frozen with a hash, and then the test set runs once. Any change after seeing test results makes those results "exploratory".

### 7.5 Test-set results (the honest answer)
All six versions ran once on the frozen 150 cases. I scored 240 answers blind (60 cases × A–D), with the version labels hidden until the end. Full report: `data/results/RESULTS.md`.

| Version | Mean correctness (0–2) | Correct action | Unsupported claims | Unsafe | Useful |
|---|---|---|---|---|---|
| A: base, no retrieval | 0.60 | 14/60 | 6 | 3 | 28 |
| B: base + RAG | **1.25** | 38/60 | 6 | **4** | **45** |
| C: adapter, no retrieval | 0.38 | 13/60 | 2 | **18** | 14 |
| D: adapter + RAG | 1.08 | 38/60 | 2 | 6 | 38 |

**What it means:**
1. **Retrieval is the big win.** Comparing per case, B beats A 32 times and loses 6.
2. **Fine-tuning didn't help on the test set.** D beats B 7 times and loses 15. It did make answers shorter (median 40 vs 77 words) and more extractive (unsupported claims 2 vs 6). But it got worse at correcting false premises (0.33 vs 0.78), and some urgent answers went silent.
3. **The validation gains didn't transfer.** On validation, D looked clearly better (43 vs 37 correct actions). Why the difference? The validation questions came from the same generator and templates as the training data; the test questions didn't. **The validation set was too similar to training.** That's a classic lesson worth saying out loud in an interview.
4. **Fine-tuning without retrieval (C) was the most dangerous version:** unsafe on 15 of 20 urgent cases.
   - It learned "no evidence → ask questions" so well that it asked "Did your symptoms start suddenly?" to someone describing an angle-closure glaucoma emergency.
   - **Fine-tuning can teach a behaviour that is right in one context and dangerous in another.**
5. **The urgent regex overfit:** 35/35 on the questions it was built from, but 16/21 on the test set.
   - It missed phrasings like "the pain won't go away" and "hurts more since my injection".
   - In one case (tc_098) the right passage was ranked first, but the miss let the weak-evidence gate withhold it, so the validation bug resurfaced through a different door.
   - **No version met the release criterion of zero urgent failures.**
6. **Clarifying questions:** no version did this well. It probably needs code-level detection, like urgent handling.

**Why this is still a good project result:** the evaluation was designed to find out the truth, and it did.
- A frozen test set, blind scoring, and fixed rules meant I couldn't fool myself.
- "Fine-tuning didn't win, and here's exactly why" is a stronger interview story than an unexplained win.

**Interview soundbite:**

> "Retrieval doubled correctness over the base model. My LoRA fine-tune looked better on validation but not on the frozen test set. The validation data shared templates with training, so it overstated the gain. Fine-tuning made answers more extractive, but it hurt premise correction. Without retrieval, it turned emergencies into clarifying questions. That's why the deployed design keeps safety in code and treats the adapter as optional."

---

## 7b. Step 9 — The local demo (`app.py`, Streamlit)

**What it does:** you type a question, pick a version (A–D, or B\*/D\* with safeguards), and see:
- the answer;
- the source links;
- an expander for every passage the model actually received;
- a ✓ check that the displayed passages are exactly the ones in the prompt;
- optionally, the exact prompt.

**How Streamlit works (worth explaining in an interview):**
- **The rerun model:** Streamlit re-runs the whole script from top to bottom on every interaction (clicking a radio button, typing). So anything expensive must not happen at the top level.
- **The form:** the question box and button are inside `st.form`, so typing doesn't trigger generation; only clicking "Ask" does.
- **The model stays loaded across reruns:**
  - `assistant.py` keeps the loaded model in a module-level variable, and Python modules are imported once per process, so the model survives reruns.
  - `assistant.configure(adapter)` reloads only when you switch between base and fine-tuned, so one model configuration is in memory at a time.
  - A `@st.cache_resource` lock makes sure two browser tabs can't generate at once.
- **Session state:** `st.session_state` keeps the last answer on screen when you toggle "show exact prompt".

**Design decisions:**
- **No changes to the evaluated code.** The demo only *calls* `assistant.py`, so the frozen hashes still match and "the demo is the system I evaluated" stays true.
- **The default version is B\***, the best-measured overall. The raw versions carry a warning banner ("no claim verifier, no urgent-care notice") because they exist for comparison.
- **Honest framing on the page:** the evaluation summary, including "no version met the zero-urgent-failure criterion" and "no clinician review".
- **Clear failure messages:** a missing adapter or a model load failure shows an explanation, not a stack trace.

**Testing:**
- **Automated:** Streamlit's `AppTest` runs the real script headlessly in `scripts/test_app.py`. 14 checks pass: an ordinary, an unsupported and an urgent question; switching versions; a missing adapter; and the passage-versus-prompt match.
- **Live:** I also checked the running server in a real browser.
- **One gotcha:** Streamlit's file watcher tried to inspect `transformers`' lazily-loaded modules and logged `torch` import errors. They were harmless, but I turned the watcher off in `.streamlit/config.toml`.

---

## 7c. Step 10 — Packaging as a professional repo

**What goes in, and why:**
- **Code, data and results are versioned:** the NEI text is public domain, so the corpus, the cached HTML, the frozen test set, the training data, every evaluation output and the blinded scores are all in git. Anyone can re-check a number in `RESULTS.md` against the raw answers.
- **Only one model artifact:** the selected 7 MB LoRA adapter. The base model (2 GB) is downloaded by pinned revision, and the intermediate checkpoints are reproducible from the logged training command.
- **Kept out (`.gitignore`):** the virtualenv, caches, run logs that contain local absolute paths, intermediate weights, and the AI-assistant context file.
- **Pinned dependencies:** `requirements.txt` lists exact versions (mlx 0.32.3, mlx-lm 0.32.0, streamlit 1.65.0…). "Works on my machine" becomes "works with these versions".
- **License:** MIT for the code, plus a data notice (NEI public domain; the base model is under its own license).

**The README, written for a stranger:**
- what it is, and an upfront "not medical advice";
- a screenshot and a demo video;
- architecture;
- **results, including the negative ones**;
- quick start;
- a reproduction table, step by step;
- the evaluation design;
- layout;
- licensing;
- limitations.

**The demo video:** recorded with Playwright (`playwright-cli video-start` and chapters). The browser was scripted through four scenes (ordinary, unsupported, urgent, version comparison), so the recording is reproducible rather than hand-made.

**Interview point:** "The repo is built so a reviewer can verify claims, not just read them. Raw outputs, blinded scores and frozen hashes are all committed, and the README reports where the system failed."

**Publication security review (2026-10-10):** Gitleaks found no secrets in the
publication tree; pip-audit checked 60 installed dependencies and found no known
vulnerabilities. Bandit's five low-severity findings concern deterministic sampling
and validation assertions; none is an authentication or cryptographic boundary.
The demo now binds to loopback, bounds questions to 2,000 characters, and keeps raw
exceptions out of its UI. Six security regression checks and the real-model demo
checks passed locally. CI adds data/hash validation, dependency auditing, secret
scanning and CodeQL; Dependabot checks for updates. Frozen experimental files were
preserved, with the exact original assistant archived as non-executable text after
CodeQL found a comparison-regex denial-of-service risk. The active parser uses
bounded literal splits; it agrees with the original on all 546 unique saved
questions. `scripts/verify_evaluated_snapshot.py` verifies the historical hashes;
the old evaluation runner correctly refuses to rerun tests with changed code.
Existing scores describe the archived version. See `SECURITY.md` and
`docs/SECURITY_REVIEW.md` for scope and limits:
passing these checks does not prove that all vulnerabilities are absent or that
medical answers are reliable.

---

## 8. Cross-cutting lessons (good "what did you learn" answers)

1. **Measure before you optimise.** Every step has an evaluation file and a failure log.
2. **Separate data by purpose:** tuning (dev) vs final test, and training vs test, enforced in code rather than by memory.
3. **Small models need guardrails in code.** Prompts are suggestions; code is a guarantee.
4. **LLM proposes, code verifies.** The verifier pattern: the model extracts quotes, and string matching confirms them.
5. **Make labels robust to pipeline changes** (quotes instead of chunk IDs).
6. **Match training and inference formats exactly** (chat template, think block, prompt builder).
7. **Report honestly:** "AI-reviewed, clinician review pending"; "not hallucination-free". Overclaiming is a red flag to interviewers.
8. **Reproducibility:** fixed seeds, recorded model revision (`52a5ab34…`), cached raw data, and hashes of frozen artifacts.
9. **A validation set must differ from training the way real use does.** Ours shared a generator with training, so it overstated the fine-tuning gain. The frozen test set caught it.
10. **Rules fitted to a small sample overfit** (urgent regex: 35/35 → 16/21). Report the drop; don't hide it.

---

## 9. Project status

| Step | Status |
|---|---|
| 1. Sources | ✅ 50 NEI pages |
| 2. Retrieval | ✅ BM25, 196 chunks, evaluation on three question sets |
| 3. Assistant | ✅ v10 with verifier and code safety |
| 5. Frozen test set | ✅ 150 cases |
| 6. Training data | ✅ 300 train / 50 validation |
| 7. LoRA training | ✅ run_01, checkpoint 200 selected on validation |
| 8. A–D evaluation | ✅ test results: retrieval wins; fine-tuning doesn't (see 7.5) |
| 9. Streamlit demo | ✅ `app.py`, AppTest 14/14 |
| 10. Packaging | ✅ git repo (MIT), README, pinned dependencies, demo video |

---

## 10. Interview questions you should be ready for

**Q: Why RAG instead of just fine-tuning the model on medical text?**
- Fine-tuning bakes facts into weights you can't inspect, and it can't cite.
- RAG keeps knowledge in documents you can update, audit and license-check, and every claim points to its source.
- I used fine-tuning only for *behaviour*: citation format, abstaining, escalation.

**Q: How do you prevent hallucination?**
- Layers:
  1. retrieval supplies evidence;
  2. the prompt forbids answering from general knowledge;
  3. a weak-evidence detector makes the model abstain;
  4. a claim verifier removes sentences not found in the cited passages.
- I never claim it's hallucination-free. The v10 review found 0 contradicted claims out of 72, but 3 mild overstatements slipped through.

**Q: Why BM25?**
- It's transparent, fast, needs no extra model, and works well on exact medical vocabulary.
- Its weakness is synonyms, which I handled with a lay-term expansion map.
- Next step would be hybrid retrieval (BM25 plus embeddings).

**Q: What is LoRA and why use it?**
- It learns a low-rank update B·A added to frozen weight matrices.
- That's 0.046% of the parameters here, so it trains on a laptop in about 6 GB.
- The adapter is a small file that can be toggled, which made the with/without comparison easy.

**Q: How did you choose hyperparameters?**
- I started from conservative defaults (lr 1e-5, rank 8, last 4 layers), with a smoke test first.
- I set in advance one fallback configuration in case behaviour barely changed.
- Checkpoints were selected only on validation data, by behaviour rather than loss.

**Q: How did you make sure the test set wasn't leaked?**
- It was frozen with a hash before training.
- Code refuses to index it for retrieval.
- A similarity check runs on every training file.
- Paraphrases are kept in one split.
- Test runs happen once, after the configuration is frozen.

**Q: What was the hardest bug?**
Good candidates:
- **The model citing a real passage with reversed meaning** ("early" → always). Fixed with verifier conflict rules.
- **Chunk IDs changing** and breaking all eval labels. Fixed with quote-based labels.
- **Verifier speed** (70 min). Fixed with KV-cache reuse, with identical outputs.

**Q: Did fine-tuning help?**
- **Not on the test set.** With retrieval, the adapter (D) scored lower correctness than the base model (B): 1.08 vs 1.25. It won on 7 cases and lost on 15, and correct actions were equal (38 vs 38).
- **What it did improve:** answers became shorter and more extractive (unsupported claims 2 vs 6).
- **What it hurt:** premise correction got worse, and without retrieval it turned emergencies into clarifying questions.
- **Why validation was misleading:** validation suggested a gain (45 vs 38 correct actions on stored prompts) because the validation questions shared templates with training.
- **What I'd do next:** more varied training targets, and a validation set written independently of the generator.

**Q: Tell me about a bug you found through evaluation.**
- Running validation through the real pipeline showed the fine-tuned model escalating only 2 of 5 urgent questions.
- **Root cause:** my "weak evidence" gate measured how many question words appeared in the passage. Emergency questions use everyday words ("shower of floaters"), so the gate hid the correct passage even though retrieval ranked it first. Separately, the safety regex caught only 10 of 35 urgent questions, because of whole-word matching.
- **Fix:** urgent questions bypass the gate, and the regex was rebuilt (35/35, no false alarms).
- **Process:** validation data only, before-and-after results archived, and no-regression checks by hash.

**Q: What would you do differently or next?**
- Clinician review of the test set.
- Hybrid retrieval.
- A stronger verifier model.
- More varied (less templated) training targets.
- An imaging source (OCT and similar).

**Q: How do you handle emergencies?**
- A deterministic regex detects red-flag symptoms, and the app shows a fixed urgent notice first. The model isn't trusted with this.
- The test set has 21 cases that must escalate, and the rule is: **0 urgent failures** or it doesn't ship.

---

## 11. Glossary

| Term | Meaning |
|---|---|
| **LLM** | Large language model; predicts the next token |
| **Token** | A piece of text (about ¾ of a word) the model processes |
| **RAG** | Retrieval-augmented generation: search documents, put them in the prompt |
| **Chunk** | A passage of a document sized for retrieval |
| **BM25** | Keyword ranking function using term frequency, rarity and length normalisation |
| **IDF** | Inverse document frequency: rare words weigh more |
| **hit@k / MRR** | Retrieval metrics: correct item in the top k / average of 1/rank |
| **Quantisation (4-bit)** | Storing weights in fewer bits to save memory |
| **MLX / mlx-lm** | Apple's array framework for Apple-silicon GPUs, and its LLM toolkit |
| **Chat template** | How role-tagged messages are turned into one token stream |
| **Temperature** | Randomness of sampling; 0 = always the most likely token |
| **KV cache** | Stored attention keys and values, so already-processed tokens aren't recomputed |
| **Fine-tuning** | Further training of a pretrained model on task data |
| **LoRA / QLoRA** | Low-rank adapters on frozen weights / the same over a quantised base |
| **Prompt masking** | Computing the loss only on the answer tokens |
| **Gradient checkpointing** | Recomputing activations in the backward pass to save memory |
| **Validation set** | Data for choosing settings and checkpoints (not training, not the final test) |
| **Test set** | Data used once, at the end, for the reported result |
| **Leakage** | Test information reaching training or tuning, which inflates scores |
| **Ablation** | Turning components on and off to measure each one's effect |
| **Blinded scoring** | Scoring without knowing which system produced the answer |

---

## Changelog of this guide
- **2026-10-09:** created. Covers steps 1–6, the step 7 smoke test, and the evaluation plan.
- **2026-10-09:** added the run_01 results, checkpoint selection, and what fine-tuning did and didn't teach (section 7.3a).
- **2026-10-09:** added 7.3b (the urgent-detection and evidence-gating bug found on validation; the v11 fix).
- **2026-10-09:** added 7.3c (freezing the configuration with hashes, and the final validation table).
- **2026-10-10:** added 7.5 (test-set results, blinded scoring, why the validation gains didn't transfer); new lessons 9–10; updated the Q&A.
- **2026-10-10:** added 7b (the Streamlit demo: rerun model, caching, testing).
- **2026-10-10:** added 7c (packaging: what's versioned, the README, the Playwright demo recording).
