from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatabaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    values: dict[str, Any]
    reason: str = Field(min_length=1, max_length=1000)


class DatabaseDelete(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: dict[str, Any]
    expected_etag: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str = Field(min_length=1, max_length=1000)


class DatabaseUpdate(DatabaseDelete):
    values: dict[str, Any] = Field(min_length=1)


class DatabaseRow(BaseModel):
    key: dict[str, Any]
    values: dict[str, Any]
    etag: str


class DatabaseWriteResult(DatabaseRow):
    change_id: int


class DatabaseRows(BaseModel):
    rows: list[DatabaseRow]
    limit: int
    offset: int
    next_offset: int | None


class DatabaseTable(BaseModel):
    name: str
    primary_key: list[str]
    writable: bool


class DatabaseSchema(DatabaseTable):
    columns: list[dict[str, Any]]
    foreign_keys: list[dict[str, Any]]
    unique_constraints: list[dict[str, Any]]
    check_constraints: list[dict[str, Any]]
    indexes: list[dict[str, Any]]
