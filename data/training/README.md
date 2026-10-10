# OphthoGuide fine-tuning data (v1)

| File | Contents |
|---|---|
| `train.jsonl` | 300 examples, mlx-lm chat format: `{"messages": [system, user, assistant]}` |
| `valid.jsonl` | 50 examples, same format, separate questions |
| `review_notes.jsonl` | One record per example: behaviour, source, evidence type, supplied and cited passages, injected/trimmed flags, token count, auto-check, manual-review note, clinical-review status. **Not training input.** |
| `src/specs.py` | Hand-written inputs: vague-symptom questions with curated possibilities, out-of-scope questions, misconceptions with correcting quotes, urgent scenarios with guidance quotes |
| `../../scripts/build_training_data.py` | Builds everything (deterministic seed) |

## Composition

| Behaviour | Train | Valid |
|---|---|---|
| Explanation with evidence | 150 | 25 |
| Asking for missing information | 50 | 8 |
| Abstaining (evidence inadequate) | 40 | 7 |
| Correcting a false premise | 30 | 5 |
| Urgent-care escalation | 30 | 5 |

**Evidence (train):**

| Evidence type | Examples |
|---|---|
| Useful passages mixed with distractors | 229 |
| All passages useful | 7 |
| Empty ("NO USABLE EVIDENCE") | 57 |
| Irrelevant passages only | 7 |

## How the examples match the application
- **System prompt:** exactly `assistant.SYSTEM_PROMPT` in every example.
- **User message:** exactly `assistant.build_user_message(question, retrieve_evidence(question))`, the same format the app uses.
- **Chat template:** mlx-lm's `ChatDataset` uses the default Qwen3 template. It adds an empty `<think>\n\n</think>\n\n` before each answer, which is identical to inference with `enable_thinking=False`. Rendered samples were checked, and no target contains thinking text.
- **Masking caveat:** with `--mask-prompt`, the empty think block (~4 tokens) falls inside the loss. That's harmless, but expected.

## How the targets were made and checked
- **Extractive.** Medical content is verbatim NEI sentences or list items from the supplied passages, cited as `[chunk_id]`. Only a small, fixed set of non-medical framing sentences is added (e.g. "Please get care now.", "Not quite.", the clarifying questions, the disclaimer).
- **Automatic checks against the prompt as rendered:**
  - every medical unit appears (near-)verbatim in a passage cited in its paragraph;
  - only supplied passages are cited;
  - no citations when evidence is empty;
  - urgent targets lead with the care instruction;
  - the disclaimer is present;
  - no placeholder or thinking text.
- **Token budget.** Every complete example is ≤ 1,800 tokens (median 1,427; answers median 97, max 356).
  - Only evidence was shortened, never answers (224/300 examples trimmed).
  - One example that couldn't fit was skipped and replaced.
- **Test-set separation.** `build_test_cases.py --check-train` passes on both files.
- **Train vs valid.** One example per source section or question, and near-duplicates are removed before splitting.

### Manual review (by Claude, from the NEI text)
- **Urgent, false premise and abstain:** every candidate was read in full.
- **Clarify:** all curated per-symptom content was read.
- **Explanation:** a random sample of 40, plus every list case.

**Fixed after review:**
- dangling references ("these problems", "the spots", "This…");
- truncated lists (lists are now always complete);
- lists that span two chunks (now cited per chunk);
- a mis-attached risk list on "Anyone can get dry eye";
- one abstain item on a topic the sources partly address (removed);
- one weak false-premise example (replaced);
- irrelevant automatically chosen clarify content (replaced with curated content).

**Clinical review: PENDING.** No clinician has reviewed these examples.

## Known limitations
- **Evidence is shorter in training than at inference.** Inference prompts carry 4 full chunks (~1,850–1,950 tokens). Consider trimming evidence at inference the same way.
- **39 training examples had the needed passage injected** in place of the lowest-ranked retrieved passage.
- **The templated framing has little variety**, so the model may learn the templates rather than the judgement behind them. Watch validation loss, and check behaviour on the frozen test set.
- **Answers are written in NEI's voice.** They are extractive and second person, which favours faithfulness over fluent paraphrase.

## Rebuild
```
.venv/bin/python scripts/build_training_data.py
.venv/bin/python scripts/build_test_cases.py --check-train data/training/train.jsonl
.venv/bin/python scripts/build_test_cases.py --check-train data/training/valid.jsonl
```
