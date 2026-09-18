from typing import Literal

from pydantic import BaseModel


class UsuarioIn(BaseModel):
    nombre: str
    email: str
    rol: Literal["responsable", "operador"] = "operador"


class UsuarioOut(UsuarioIn):
    id: int


class LoginIn(BaseModel):
    email: str
