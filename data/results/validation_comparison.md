# Step 7: Checkpoint selection and base vs adapter on validation

**Data:** the 50 validation prompts exactly as stored in `data/training/valid.jsonl`. These are the same prompts the model was trained on in format (evidence trimmed to fit the budget). No test cases were used.

**Generation:** temperature 0.2, top_p 0.9, max 700 tokens, and a fixed seed per example, identical for every model. Raw model output: no verifier, no urgent notice.

**Checks:** the heuristic checks in `scripts/score_versions.py`. The action classifier labels 349 of the 350 gold targets correctly.

## Training (run_01)
**Settings:**
- Qwen3-4B-MLX-4bit, revision `52a5ab34`;
- LoRA rank 8, scale 20, last 4 of 36 blocks, 1.835M trainable parameters (0.046%);
- lr 1e-5, Adam, batch 1, 300 iterations (1 epoch);
- `--mask-prompt`, gradient checkpointing, max sequence length 2,048, seed 42.

**Run:** peak memory 6.2 GB, 0 swaps, about 6 s per iteration.

| Iteration | 0 | 50 | 100 | 150 | 200 | 250 | 300 |
|---|---|---|---|---|---|---|---|
| Validation loss | 2.232 | 0.383 | 0.315 | 0.263 | 0.233 | 0.211 | 0.199 |

**Notes:**
- Loss falls fast because targets are extractive and templated: copying from the evidence is easy to predict. Loss does not measure safety, so checkpoints were selected on behaviour.
- The 50-iteration smoke test reproduced iteration 50 exactly (0.383), so runs are deterministic with the same seed.
- The pre-set fallback (run_02: 16 layers, lr 5e-5) was **not triggered**. Behaviour changed clearly, and loss fell by much more than 10%.

## Checkpoint comparison
"Problems" counts four things: invalid citations, citations on empty evidence, low-support cited sentences, and repetitive answers.

| Model | Action OK | Explain | Clarify | Abstain | Premise | Urgent | Problems | Median words |
|---|---|---|---|---|---|---|---|---|
| base | 38/50 | 25/25 | 0/8 | 6/7 | 5/5 | 2/5 | 34 | 82 |
| ckpt 50 | 37/50 | 23/25 | 2/8 | 6/7 | 5/5 | 1/5 | 15 | 56 |
| ckpt 100 | 40/50 | 24/25 | 2/8 | 6/7 | 5/5 | 3/5 | 15 | 52 |
| ckpt 150 | 39/50 | 24/25 | 1/8 | 5/7 | 4/5 | 5/5 | 14 | 44 |
| **ckpt 200 (selected)** | **45/50** | 25/25 | 4/8 | 6/7 | 5/5 | 5/5 | 10 | 63 |
| ckpt 250 | 41/50 | 25/25 | 0/8 | 6/7 | 5/5 | 5/5 | 8 | 52 |
| ckpt 300 | 41/50 | 25/25 | 2/8 | 5/7 | 4/5 | 5/5 | 11 | 61 |

**Selection rule (set in advance):** most action-OK answers, then fewest problems, then lowest loss. That gives **checkpoint 200**, now copied to `adapters/selected/` (`SELECTED.json`).

**Caution:** with 50 examples, and only 5–8 per behaviour, differences of 2–4 answers are within noise. The clarify column swings from 0 to 4 between neighbouring checkpoints.

## Reading the answers (base vs ckpt 200, all clarify, urgent, abstain and premise items, plus 8 explanations)

**Better with the adapter:**
- **Urgent:** all 5 lead with the care instruction (base: 2/5). The base model often restated the question or explained first, and put the "call right away" sentence second or third.
- **Explanations:** closer to the source wording, with lists kept complete. Less padding, e.g. the base model added "These complications are outlined in the evidence provided". Median length fell from 82 to 63 words.
- **Clarify with no evidence:** asks focused questions ("Did it start suddenly? One eye or both?"). The base model only said "sources don't cover this".
- **Citation problems:** 10 vs 34 flags.

**Worse with the adapter, or new failure modes:**
- **Unsupported content after an abstain opening (valid_025).**
  - The adapter wrote "My sources don't cover this", then added three unsupported statements about eye infections, vaccines and antibiotics.
  - The base model abstained cleanly. **This is the most serious regression.**
  - The new `content_on_empty` metric catches it: 1 of 10 empty-evidence answers for ckpt 200 vs 0 for base.
- **Repetition loop (valid_034):** a clarifying question repeated until the token limit.
- **Clarify with useful evidence:** the adapter usually answers or gives a short "see your doctor", instead of listing possibilities and then asking. 4 of 8 clarify answers were correct, all of them on empty evidence.
- **Premise corrections are weaker.** The adapter says "No." and then often only "the passages don't state that…" (valid_030, valid_040), instead of giving the source's actual correcting fact. The training targets did give that fact.
- **It copied the internal NO_EVIDENCE text into answers** ("no passage matched at least 50% of the question's terms"). That's harmless but unnatural.
- **Clarify red-flag line dropped:** the closing "If your symptoms are severe or came on suddenly, please see an eye doctor" line from the targets was often dropped.

**Takeaway:** the adapter learned the *format* well: lead with urgency, cite, keep the source wording, ask questions when evidence is empty. It did not reliably learn *judgement* (when to clarify vs answer) or *restraint* after an abstain opening. That matches the step 6 risk noted in the README: templated targets can teach templates rather than judgement.

## Next
Run versions A–D, B\* and D\* on the validation questions under app conditions (fresh retrieval, untrimmed evidence), check the harness, then freeze the configuration and run the 150 test cases once.
