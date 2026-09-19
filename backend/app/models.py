"""Every table registered on `Base.metadata`, for Alembic."""

from app.core.database import Base
from app.core.events import Event
from app.features.decisions.model import Decision, DecisionReview, Finding
from app.features.ingestion.model import File, Instance
from app.features.learning.model import Adoption, Analysis, Proposal, Validation
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.rules.model import NormRule, Rule
from app.features.sources.model import Source
from app.features.use_cases.model import AgentConfig, UseCase
from app.features.users.model import User

__all__ = [
    "Adoption",
    "Analysis",
    "Proposal",
    "Validation",
    "AgentConfig",
    "Base",
    "Decision",
    "DecisionReview",
    "DecisionType",
    "Event",
    "File",
    "Finding",
    "Instance",
    "NormRule",
    "Process",
    "Rule",
    "Source",
    "Symbol",
    "UseCase",
    "User",
]
