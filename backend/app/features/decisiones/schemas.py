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


class CambioOut(BaseModel):
    instancia_id: int
    nombre: str
    antes: str
    despues: str
    autor_anterior: str
    motivo: str


class ImpactoOut(BaseModel):
    """What a rule change would do to the decisions already taken."""

    sin_cambio: int
    cambios: list[CambioOut]  # the engine decided it and would now decide otherwise
    conflictos: list[CambioOut]  # a person decided it and the rules would contradict them


class HallazgoOut(BaseModel):
    id: int
    decision_id: int
    regla_id: int | None
    tipo: str
    detalle: str | None
    creado: datetime
