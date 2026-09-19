from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, from the environment or `.env` (prefix `TRACE_`)."""

    model_config = SettingsConfigDict(env_prefix="TRACE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://trace:trace@localhost:5432/trace"
    # Process packs, where a source's connector configuration lives (`<pack>/sources.json`).
    # In Docker this resolves to the /processes mount.
    processes_dir: Path = Path(__file__).resolve().parents[3] / "processes"
    # One model per agent role, in PydanticAI's `provider:model` form (ADR 0006). The two
    # compilers must differ: their disagreement is what catches a misread rule (ADR 0004).
    compiler_a_model: str = "anthropic:claude-opus-5"
    compiler_b_model: str = "openai:gpt-5"
    assistant_model: str = "anthropic:claude-opus-5"


settings = Settings()
