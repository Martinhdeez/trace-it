from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ROLES = ("compiler_a", "compiler_b", "extractor_1", "extractor_2", "assistant")


class LLMConfig(Base):
    """Provider and model per role, in LiteLLM format ("anthropic/claude-opus-5").
    Changeable at runtime (P22)."""

    __tablename__ = "llm_config"

    role: Mapped[str] = mapped_column(primary_key=True)
    model: Mapped[str]
