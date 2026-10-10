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
- Source validation, test manifest verification, and the seven frozen configuration
  hashes passed. Security hardening changes the demo wrapper and packaging;
  the frozen assistant, retrieval, evaluation runner, corpus, and adapter are intact.
- Four security regression checks and the existing real-model demo checks passed
  locally. All 18 Python source files compile. The five screenshots and sampled
  frames from the 2-minute-11-second video contained no visible private information;
  the video has no audio track and its metadata contains no personal paths.

## Hardening

- Ignore environment files, private keys, local agent settings and service secrets.
- Bind the demo to loopback with XSRF/CORS protections enabled.
- Bound question length and avoid exposing raw exceptions or missing-adapter paths.
- Add least-privilege CI, commit-pinned Actions, dependency auditing, and Dependabot.
- Add Gitleaks history scans and CodeQL. Hosted results are recorded by GitHub
  Actions; local checks alone do not establish that hosted jobs pass.

## Limits

Scanners detect known patterns and published advisories, not every vulnerability.
The model can be manipulated through input, and its answers can be wrong. The
test evaluation failed the project's urgent-safety release criterion. Clinician
review is pending. Keep the public demo local and do not use it for diagnosis,
triage, or patient-care decisions.
