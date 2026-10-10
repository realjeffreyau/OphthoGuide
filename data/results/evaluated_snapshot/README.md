# Historical evaluated assistant

`assistant.py.txt` is the exact assistant source used for the published experiment,
stored as non-executable text. Its SHA-256 matches `scripts/assistant.py` in
`../FROZEN_CONFIG.json`. Verify it with `scripts/verify_evaluated_snapshot.py`.

CodeQL identified a polynomial-time regex in its comparison-question parser.
The active assistant replaces that regex with bounded literal parsing. The old
snapshot is for auditing the experiment, not for running a service or processing
untrusted input. Published scores describe this archived version; the hardened
version has not received a new held-out medical evaluation.

The original `run_versions.py` intentionally rejects a new test run using the
changed active assistant. Do not refreeze or overwrite the old experiment merely
to bypass that guard. New experiments require separately versioned configurations
and a new held-out set.
