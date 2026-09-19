"""Every instruction a model receives lives in a `prompts/` folder beside its feature.

Two folders today: `features/agents/prompts/` (the rule and decision agents, ADR 0004) and
`features/ingestion/prompts/` (the readers: transcription, the text judge, field selection).
Keeping them out of the Python means they can be read, reviewed and diffed on their own, and
a published process version can snapshot the exact text a decision was taken with (ADR 0018).

Files are read on every call, so editing one takes effect on the next request without a
restart. A prompt's text is part of the provider journal's cache key: change it and the
stored answers for the old text are no longer reused.
"""

from pathlib import Path


def read(directory: Path, *names: str) -> str:
    """The prompts `<directory>/<name>.md`, stripped and joined by a blank line."""
    return "\n\n".join(
        (directory / f"{name}.md").read_text(encoding="utf-8").strip() for name in names
    )
