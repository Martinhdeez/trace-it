from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, from the environment or `.env` (prefix `TRACE_`)."""

    model_config = SettingsConfigDict(env_prefix="TRACE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://trace:trace@localhost:5432/trace"
    # Process packs, where a source's connector configuration lives (`<pack>/sources.json`).
    # In Docker this resolves to the /processes mount.
    processes_dir: Path = Path(__file__).resolve().parents[3] / "processes"
    # One model per agent role, in PydanticAI's `provider:model` form (ADR 0006): any
    # provider PydanticAI supports. The tester writes the tests the compiler's code must
    # pass; a different provider makes a shared misreading less likely (ADR 0004).
    compiler_model: str = "anthropic:claude-opus-5"
    tester_model: str = "openai:gpt-5"
    assistant_model: str = "anthropic:claude-opus-5"
    normalizer_model: str = "anthropic:claude-opus-5"
    # Helmcode, an OpenAI-compatible API: select it with `helmcode:<model>` (e.g.
    # `helmcode:deepseek-v4-flash`). Its key is read like every provider's: HELMCODE_API_KEY.
    helmcode_base_url: str = "https://api.helmcode.com/v1"
    # A compiled rule activates by itself when it would change at most this share of the
    # decisions already taken and contradicts no decision a person took (ADR 0004).
    auto_activate_max_change: float = 0.05
    # Rules one background job compiles at once (Helmcode allows 5 concurrent requests
    # per model).
    compile_concurrency: int = 5


settings = Settings()
