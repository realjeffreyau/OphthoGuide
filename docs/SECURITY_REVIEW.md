# Publication security review — 2026-10-10

Scope: the curated Git tree, application input and rendering, local configuration,
dependencies, evaluation integrity, and demo media. This is a source publication,
not deployment of a public medical service.

## Checks

- Gitleaks 8.30.1 found no secrets in the candidate publication tree. A separate
  path scan found no personal absolute paths. The repository initially had no
  commits, so no earlier history required cleanup.
- pip-audit 2.10.1 checked 60 installed dependencies against its advisory service
  and found no known vulnerabilities. `pip check` reported no broken requirements.
- Bandit 1.9.4 found no medium or high severity findings. Low severity findings
  were two validation assertions and three deterministic random-sampling sites.
  These sites do not protect an authentication or cryptographic boundary.
- AgentShield was run against the public tree. It found no applicable agent
  configuration files: local `CLAUDE.md` and `.claude/` are excluded. Its empty
  result is not an application security assessment.
- Source validation and test manifest verification passed. All seven historical
  evaluation hashes pass against the archived assistant and unchanged remaining
  artifacts. The active assistant has a post-evaluation security patch; the old
  runner deliberately refuses a new test run with that changed source.
- Six security regression checks and the existing real-model demo checks passed
  locally. The five screenshots and sampled
  frames from the 2-minute-11-second video contained no visible private information;
  the video has no audio track and its metadata contains no personal paths.

## Hardening

- Ignore environment files, private keys, local agent settings and service secrets.
- Bind the demo to loopback with XSRF/CORS protections enabled.
- Bound question length and avoid exposing raw exceptions or missing-adapter paths.
- Add least-privilege CI, commit-pinned Actions, dependency auditing, and Dependabot.
- CodeQL detected one high-severity polynomial-regex denial-of-service risk in
  comparison parsing. Replace it with bounded literal parsing; hostile million-
  character inputs return immediately. Compatibility checks on 546 unique saved
  questions found no differences in parsed comparison parts. This is a parser
  compatibility check, not a new medical evaluation.
- Add Gitleaks history scans and CodeQL. Hosted results are recorded by GitHub
  Actions; local checks alone do not establish that hosted jobs pass.

## Limits

Scanners detect known patterns and published advisories, not every vulnerability.
The model can be manipulated through input, and its answers can be wrong. The
test evaluation failed the project's urgent-safety release criterion. Clinician
review is pending. Keep the public demo local and do not use it for diagnosis,
triage, or patient-care decisions.
