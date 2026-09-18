from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class ReglaIn(BaseModel):
    texto: str
    tipo: Literal["requisito", "prohibicion"]
    decision: str  # must be one of the process's decision types


class ReglaOut(BaseModel):
    id: int
    proceso_id: int
    texto: str
    tipo: str
    decision: str
    estado: str
    hash: str | None
    informe: dict[str, Any] | None
    creada: datetime
    activada: datetime | None


class ReglaDetalle(ReglaOut):
    codigo_a: str | None
    codigo_b: str | None
    tests_a: list[dict[str, Any]] | None
    tests_b: list[dict[str, Any]] | None
