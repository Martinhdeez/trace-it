from pydantic import BaseModel, Field


class SimboloIO(BaseModel):
    nombre: str
    tipo: str = Field(examples=["texto", "numero", "fecha"])
    descripcion: str = ""


class TipoDecisionIO(BaseModel):
    nombre: str
    prioridad: int  # highest wins when several rules fire
    por_defecto: bool = False  # applies when no rule fires
    requiere_persona: bool = False  # goes to the human queue for a responsable


class ProcesoIn(BaseModel):
    nombre: str
    descripcion: str = ""
    tipos_decision: list[TipoDecisionIO]
    simbolos: list[SimboloIO] = []


class ProcesoOut(BaseModel):
    id: int
    nombre: str
    descripcion: str


class ProcesoDetalle(ProcesoOut):
    tipos_decision: list[TipoDecisionIO]
    simbolos: list[SimboloIO]
