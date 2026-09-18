from typing import Literal

from pydantic import BaseModel


class SuggestionOut(BaseModel):
    decision: str
    reasoning: str
    proposed_rule: str
    proposed_type: Literal["requirement", "prohibition"]
