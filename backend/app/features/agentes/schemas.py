from typing import Literal

from pydantic import BaseModel


class SugerenciaOut(BaseModel):
    decision: str
    razonamiento: str
    regla_propuesta: str
    tipo_propuesto: Literal["requisito", "prohibicion"]
