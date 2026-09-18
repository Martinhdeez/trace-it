from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRACE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://trace:trace@localhost:5432/trace"
    erp_url: str = "http://localhost:8009"
    # Process packs; in Docker this resolves to the /processes mount.
    processes_dir: Path = Path(__file__).resolve().parents[3] / "processes"


settings = Settings()
