from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DecisionOut(BaseModel):
    id: int
    decision: str
    autor: str  # "motor" or the person's name
    motivo: str | None
    resultados: list[dict[str, Any]]  # per rule: regla_id, hash, salta, motivo
    reglas_hash: str
    creada: datetime


class EventoOut(BaseModel):
    paso: str
    datos: dict[str, Any] | None
    latencia_ms: int | None
    creado: datetime


class InstanciaOut(BaseModel):
    id: int
    nombre: str = Field(examples=["factura_1217.pdf"])  # the exact file_id of the export
    estado: str
    decision: str | None  # the latest decision, if any


class InstanciaDetalle(InstanciaOut):
    fichero_hash: str
    simbolos: dict[str, Any] | None
    decisiones: list[DecisionOut]  # append-only history, oldest first
    eventos: list[EventoOut]


class ResolverIn(BaseModel):
    decision: str = Field(examples=["NO_PAGAR"])  # must be a decision type of the process
    motivo: str


class ResumenEjecucion(BaseModel):
    decididas: int
    por_decision: dict[str, int] = Field(examples=[{"PAGAR": 431, "NO_PAGAR": 9, "ESCALAR": 60}])
