"""Hash tracked build inputs, independent of the commit's display/revision label."""

import argparse
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "criminal": [
        "processes/hiring-screening/criminal_records_erp.py",
        "deploy/backend.Dockerfile",
    ],
    "backend": [
        ".dockerignore",
        "deploy/compose.yml",
        "backend/app",
        "backend/alembic",
        "backend/alembic.ini",
        "backend/pyproject.toml",
        "backend/uv.lock",
        "backend/tests/golden/batch1_expected.jsonl",
        "processes",
        "deploy/backend.Dockerfile",
        "deploy/backend-start.sh",
        "docs/production-api.md",
    ],
    "frontend": [
        ".dockerignore",
        "deploy/compose.yml",
        "frontend",
        "deploy/frontend.Dockerfile",
        "deploy/nginx.conf",
    ],
}


def fingerprint(component: str, root: Path = ROOT) -> str:
    files = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--", *INPUTS[component]], cwd=root
        )
        .decode()
        .split("\0")
    )
    digest = hashlib.sha256(b"trace-it-component-v1\0")
    for name in sorted(filter(None, files)):
        path = root / name
        digest.update(name.encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=INPUTS)
    print(fingerprint(parser.parse_args().component))
