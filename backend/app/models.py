"""Every table registered on `Base.metadata`, for Alembic."""

from app.core.database import Base
from app.core.events import Event
from app.features.alerts.model import Alert
from app.features.database_api.model import DatabaseApiChange
from app.features.decisions.model import Decision, DecisionReview, Finding
from app.features.ingestion.model import File, Instance
from app.features.learning.model import Adoption, Analysis, Proposal, Validation
from app.features.mail_ingestion.model import MailAccount, MailAttachment, MailMessage, RunOperation
from app.features.processes.model import (
    DecisionType,
    DiscoveryRevision,
    DiscoverySession,
    Process,
    Symbol,
)
from app.features.proposals.model import ManagerProposal
from app.features.rules.model import NormRule, Rule
from app.features.sources.model import Source
from app.features.use_cases.model import AgentConfig, UseCase
from app.features.users.model import User
from app.features.versions.model import Execution, ProcessDraft, ProcessVersion

__all__ = [
    "DatabaseApiChange",
    "MailAccount",
    "MailAttachment",
    "MailMessage",
    "RunOperation",
    "Alert",
    "ManagerProposal",
    "Execution",
    "ProcessDraft",
    "ProcessVersion",
    "Adoption",
    "Analysis",
    "Proposal",
    "Validation",
    "AgentConfig",
    "Base",
    "Decision",
    "DecisionReview",
    "DecisionType",
    "DiscoveryRevision",
    "DiscoverySession",
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
