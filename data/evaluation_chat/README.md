# Multi-turn chat evaluation

This set is **separate** from the frozen single-turn test set in `data/evaluation/`. That set,
its results (`data/results/`) and the archived evaluated assistant are unchanged. Numbers from
the two evaluations are not comparable: different tasks, different prompts, different pipeline.

| File | Contents |
|---|---|
| `chat_cases.jsonl` | 16 scripted conversations (37 user turns) with expected behaviour per case |
| `runs_Bstar.jsonl`, `runs_Dstar.jsonl` | full transcripts: answer, raw model draft, retrieval query, supplied and cited passages, removed claims, urgency flag, patient context, seconds |
| `RESULTS.md` | automatic checks, the reviewed per-conversation scores, latency, failures |

**Case fields:**
- `id`, `category`, `turns` (the user messages, scripted so both versions see identical input);
- `expect`:
  - `final_action`: answer / answer_or_clarify / escalate / abstain_partial;
  - `urgent_from_turn`;
  - `facts`: strings that must appear in the patient context;
  - `must_not`: forbidden phrases;
- `notes`.

**Categories covered:**
- short replies;
- corrections;
- urgency that changes mid-conversation;
- topic change;
- missing, irrelevant and conflicting evidence;
- pressure for certainty;
- hypothesis vs. reported fact;
- plain-language synthesis;
- long context (truncation);
- urgent with weak retrieval.

**Review status:**
- Expected behaviour was written by Claude (an AI) from NEI pages, and the transcripts were scored by Claude.
- **No clinician review.**
- Because the conversations are scripted, they test context handling and safety behaviour. They don't test how a real person would respond to the assistant's questions.

Run: `.venv/bin/python scripts/run_chat_eval.py --version B*` (then `D*`), then
`--report B* D*`.
