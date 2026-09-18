"""Loaders for the golden files, and the cases where the reference and the rules disagree."""

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent


def _jsonl(name: str) -> list[dict[str, Any]]:
    lines = (HERE / name).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def expected() -> dict[str, dict[str, Any]]:
    """{file_id: {"expected", "confidence", "why"}} for all 500 files."""
    return {row["file_id"]: row for row in _jsonl("batch1_expected.jsonl")}


def symbols() -> list[dict[str, Any]]:
    """The symbols of the 471 text PDFs, in file_id order."""
    return _jsonl("batch1_symbols.jsonl")


# Files where the golden reference and the hand-written rule code decide differently, each
# investigated and waiting for a team decision. {file_id: reason}. Empty means none.
KNOWN_MISMATCHES: dict[str, str] = {}
