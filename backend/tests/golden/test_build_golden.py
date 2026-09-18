"""The committed golden files are exactly what the build script produces today."""

import shutil

import pytest

from tests.golden import build_golden
from tests.support import challenge

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not challenge.available(), reason="challenge submodule not checked out"),
    pytest.mark.skipif(shutil.which("pdftotext") is None, reason="needs pdftotext (poppler)"),
]


def test_golden_files_are_up_to_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(build_golden, "EXPECTED", tmp_path / "expected.jsonl")
    monkeypatch.setattr(build_golden, "SYMBOLS", tmp_path / "symbols.jsonl")

    build_golden.main()

    for built, committed in [
        (tmp_path / "expected.jsonl", build_golden.HERE / "batch1_expected.jsonl"),
        (tmp_path / "symbols.jsonl", build_golden.HERE / "batch1_symbols.jsonl"),
    ]:
        assert built.read_bytes() == committed.read_bytes(), (
            f"{committed.name} is stale: run `uv run python -m tests.golden.build_golden`"
        )
