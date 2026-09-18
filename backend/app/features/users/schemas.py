from typing import Literal

from pydantic import BaseModel


class UserIn(BaseModel):
    name: str
    email: str
    role: Literal["manager", "operator"] = "operator"


class UserOut(UserIn):
    id: int


class LoginIn(BaseModel):
    email: str
