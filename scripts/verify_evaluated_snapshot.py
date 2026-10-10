"""Verify historical evaluation hashes, including the archived pre-security-patch source."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    manifest = json.loads((ROOT / "data/results/FROZEN_CONFIG.json").read_text())
    archived = {"scripts/assistant.py": "data/results/evaluated_snapshot/assistant.py.txt"}
    for name, expected in manifest["sha256"].items():
        path = ROOT / archived.get(name, name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Historical evaluation hash mismatch: {name}")
    print(f"PASS: {len(manifest['sha256'])} historical evaluation hashes")


if __name__ == "__main__":
    main()
