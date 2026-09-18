"""Every table registered on `Base.metadata`, for Alembic."""

from app.core.database import Base
from app.features.decisiones.model import Decision, Hallazgo
from app.features.extraccion.model import Extraccion
from app.features.fuentes.model import Fuente
from app.features.ingesta.model import Fichero, Instancia
from app.features.llm.model import ConfigLLM
from app.features.procesos.model import Proceso, Simbolo, TipoDecision
from app.features.reglas.model import Regla
from app.features.trazas.model import Evento
from app.features.usuarios.model import Usuario

__all__ = [
    "Base",
    "ConfigLLM",
    "Decision",
    "Evento",
    "Extraccion",
    "Fichero",
    "Fuente",
    "Hallazgo",
    "Instancia",
    "Proceso",
    "Regla",
    "Simbolo",
    "TipoDecision",
    "Usuario",
]
