"""Validate a versioned ERP release and prepare its isolated Docker build context."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def prepare(output: Path, name: str | None = None, root: Path = HERE) -> dict:
    name = name or json.loads((root / "active.json").read_text())["release"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name):
        raise ValueError("Invalid release name")
    source = root / "releases" / name
    manifest = json.loads((source / "release.json").read_text())
    if manifest["id"] != name or not isinstance(manifest["expected_rows"], int):
        raise ValueError("Invalid release identity or row count")
    files = ["alberto_erp.py", *manifest["updates"]]
    if len(set(files)) != len(files) or set(files) != set(manifest["sha256"]):
        raise ValueError(
            "Every source and ordered update must have exactly one checksum"
        )
    for filename in files:
        if Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError("Release files must be direct children")
        path = source / filename
        if (
            path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest()
            != manifest["sha256"][filename]
        ):
            raise ValueError(f"Checksum mismatch: {name}/{filename}")
    output.mkdir(parents=True, exist_ok=False)
    for filename in [*files, "release.json"]:
        shutil.copyfile(source / filename, output / filename)
    for filename in ["server.py", "smoke.py"]:
        shutil.copyfile(root / filename, output / filename)
    shutil.copyfile(root / "release.Dockerfile", output / "Dockerfile")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", help="Defaults to the version in active.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.release)))
