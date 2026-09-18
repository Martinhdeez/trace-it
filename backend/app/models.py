"""Every table registered on `Base.metadata`, for Alembic."""

from app.core.database import Base
from app.features.decisions.model import Decision, Finding
from app.features.extraction.model import Extraction
from app.features.ingestion.model import File, Instance
from app.features.llm.model import LLMConfig
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.features.traces.model import Event
from app.features.users.model import User

__all__ = [
    "Base",
    "Decision",
    "DecisionType",
    "Event",
    "Extraction",
    "File",
    "Finding",
    "Instance",
    "LLMConfig",
    "Process",
    "Rule",
    "Source",
    "Symbol",
    "User",
]
