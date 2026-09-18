from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRACE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://trace:trace@localhost:5432/trace"
    erp_url: str = "http://localhost:8009"


settings = Settings()
