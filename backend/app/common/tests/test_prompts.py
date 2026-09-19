"""Every instruction a model receives is a file, and its text is pinned.

A prompt's text is part of the provider journal's cache key and of a published version's
snapshot, so an accidental edit silently invalidates stored answers and changes what a
decision was taken with. These hashes make such an edit a failing test, not a surprise.
Changing a prompt on purpose means changing its hash here in the same commit.
"""

import hashlib
from pathlib import Path

import pytest

from app.common import prompts
from app.features.agents import llm
from app.features.ingestion import schema_fields
from app.features.ingestion.ocr import gemini, judge, vision

AGENTS = Path(llm.__file__).parent / "prompts"
INGESTION = Path(schema_fields.__file__).parent / "prompts"

# The ten agent roles (ADR 0004) and the five reader instructions.
AGENT_PROMPTS = {
    "assistant",
    "coder",
    "decision_reviewer",
    "discovery",
    "learner",
    "normalizer",
    "process_chat",
    "reviewer",
    "shared",
    "tester",
}
READER_PROMPTS = {
    "select-fields": "7a1f63c31490",
    "text-judge": "ebdf0c98cc00",
    "transcribe-compatible": "6410f63fa628",
    "transcribe-invoice": "933f2cfe127f",
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def test_no_model_instruction_is_hidden_in_the_python():
    """A new prompt belongs in a `prompts/` folder, not in a module constant."""
    roots = [Path(llm.__file__).parents[1], Path(schema_fields.__file__).parent]
    offenders = []
    for root in roots:
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                name = line.split("=")[0].strip()
                if line.endswith(("= (", '= "')) and name in {
                    "PROMPT",
                    "INSTRUCTIONS",
                    "COMPATIBLE_PROMPT",
                    "SCHEMA_PROMPT",
                    "SYSTEM",
                }:
                    offenders.append(f"{path.name}: {line.strip()}")
    assert not offenders, "\n".join(offenders)


def test_every_agent_role_has_its_own_file():
    assert {p.stem for p in AGENTS.glob("*.md")} == AGENT_PROMPTS
    for name in AGENT_PROMPTS:
        assert llm.prompt(name).strip(), name


def test_reader_prompts_are_the_pinned_text():
    assert {p.stem for p in INGESTION.glob("*.md")} == READER_PROMPTS.keys() | {"transcribe-schema"}
    live = {
        "select-fields": schema_fields.PROMPT,
        "text-judge": judge.INSTRUCTIONS,
        "transcribe-compatible": vision.COMPATIBLE_PROMPT,
        "transcribe-invoice": gemini.PROMPT,
    }
    assert {name: digest(text) for name, text in live.items()} == READER_PROMPTS


def test_the_schema_transcription_prompt_carries_the_requested_fields():
    """Its one placeholder is filled with the fields; without fields the plain one is used."""
    assert "{fields}" in vision.SCHEMA_PROMPT
    assert digest(vision.SCHEMA_PROMPT) == "93c4b522ad80"
    filled = vision._prompt([{"name": "expires_on"}])
    assert "{fields}" not in filled and '"expires_on"' in filled
    assert vision._prompt(None) == vision.COMPATIBLE_PROMPT


def test_a_missing_prompt_file_fails_loudly():
    with pytest.raises(FileNotFoundError):
        prompts.read(INGESTION, "not-a-prompt")
