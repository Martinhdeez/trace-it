"""Evidence types shared by file ingestion and reference sources."""

from typing import Literal

from pydantic import BaseModel, Field

FieldStatus = Literal["OBSERVED", "MISSING", "INVALID", "AMBIGUOUS", "LOW_CONFIDENCE", "UNVERIFIED"]


class Evidence(BaseModel):
    locator: str
    text: str
    method: str
    page: int | None = None
    bbox: list[float] | None = None
    confidence: float | None = None
    preprocessing: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    value: str | None
    raw: str
    evidence: Evidence
    error: str | None = None


class ExtractedField(BaseModel):
    value: str | None = None
    status: FieldStatus = "MISSING"
    candidates: list[Candidate] = Field(default_factory=list)
    origin: str = "DOCUMENT"


class TextSpan(BaseModel):
    text: str
    bbox: list[float]


class TablePosition(BaseModel):
    """Geometry-derived cell membership, never an additional reader or an inferred header."""

    id: str
    row: int
    column: int
    rows: int
    columns: int


class TextLine(BaseModel):
    id: str
    page: int
    raw: str
    text: str
    bbox: list[float]
    method: str = "native"
    confidence: float | None = None
    preprocessing: list[str] = Field(default_factory=list)
    spans: list[TextSpan] = Field(default_factory=list)
    table: TablePosition | None = None
