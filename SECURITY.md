# Security

OphthoGuide is a local educational research demo. It has no authentication or
public-service rate limits. Run it on your own Mac; the checked-in Streamlit
configuration binds to `127.0.0.1`, enables CORS and XSRF protections, and disables
usage telemetry. Do not expose it to the internet without a separate hosting
security review, authentication, resource limits, and transport encryption.

Questions are held in Streamlit session memory; the demo does not write them to
disk. Pipeline and evaluation commands can write prompts and answers when you
request logs. Do not commit personal health information or private conversations.
Model setup contacts Hugging Face to download files. Inference runs locally.

The demo limits questions to 2,000 characters and keeps internal exception details
out of the UI. Model text uses Streamlit's default Markdown renderer; it is never
executed as code, SQL, shell commands, or enabled HTML. The model has no tools.
Prompt injection can still alter answers, and the verifier can miss unsupported
claims. These controls do not establish medical reliability.

Comparison parsing uses bounded literal separators instead of a backtracking
regex. The original evaluated source is retained as a non-executable historical
artifact; it contains the old regex and must not be used to serve untrusted input.
Published medical evaluation scores refer to that historical snapshot.

## Reporting

Report vulnerabilities privately through [GitHub private vulnerability reporting](https://github.com/realjeffreyau/OphthoGuide/security/advisories/new).
If that form is unavailable, contact the repository owner privately. Do not post
credentials, personal data, or exploit details in a public issue.

## Checks

GitHub Actions validates source data and frozen hashes, runs security regression
checks, scans Python with Bandit, and checks the complete pinned dependency
inventory with pip-audit. Dependabot checks Python dependencies and Actions weekly.
Gitleaks scans Git history for credentials, and CodeQL analyzes Python code.
MLX inference requires an Apple silicon Mac and is tested locally, not by the
Linux validation job.

`requirements-lock.txt` records the evaluated Mac environment. The shorter
`requirements.txt` lists direct dependencies. Dependency updates require a new
audit and reproducibility review; old experimental results describe their original
environment. See [the publication review](docs/SECURITY_REVIEW.md) for the dated
checks and their limitations.
