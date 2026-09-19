"""Non-secret extraction cache identity, independent of release and frontend changes."""

import hashlib
from pathlib import Path


def fingerprint(app_root: Path) -> str:
    files = [
        p
        for p in (app_root / "features/ingestion").rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".md", ".json"}
        and "tests" not in p.parts
        and "__pycache__" not in p.parts
    ]
    files += [
        app_root / "common/prompts.py",
        app_root / "features/processes/execution.py",
    ]
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(
            str(path.relative_to(app_root)).encode() + b"\0" + path.read_bytes() + b"\0"
        )
    digest.update((app_root.parent / "uv.lock").read_bytes())
    return digest.hexdigest()


def verify(seed, app_root: Path, snapshots: dict[str, dict]):
    if fingerprint(app_root) != seed["ocr_cache"]["code_hash"]:
        raise ValueError(
            "OCR code/dependencies changed: refresh the cached seed once before deployment"
        )
    for name, expected in seed["ocr_cache"]["extraction_settings"].items():
        actual = snapshots[name].get("execution", {}).get("extraction")
        approved_upgrade = seed["ocr_cache"].get("adopt_from", {}).get(name)
        if actual != expected and (
            approved_upgrade is None or actual != approved_upgrade
        ):
            raise ValueError(
                f"OCR settings changed for {name}: refresh the cached seed before deployment"
            )
    for name, expected in seed["ocr_cache"].get("symbol_schemas", {}).items():
        if snapshots[name]["process"]["symbols"] != expected:
            raise ValueError(f"OCR schema changed for {name}: refresh the cached seed")
