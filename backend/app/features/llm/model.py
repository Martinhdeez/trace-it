from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

PAPELES = ("compilador_a", "compilador_b", "extractor_1", "extractor_2", "asistente")


class ConfigLLM(Base):
    """Provider and model per role, in LiteLLM format ("anthropic/claude-opus-5").
    Changeable at runtime (P22)."""

    __tablename__ = "config_llm"

    papel: Mapped[str] = mapped_column(primary_key=True)
    modelo: Mapped[str]
