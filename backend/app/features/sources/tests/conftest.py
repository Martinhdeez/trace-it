from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class Limits:
    max_excel_rows: int = 25_000
    max_excel_cols: int = 100
    max_excel_cells: int = 500_000


@pytest.fixture
def settings():
    return Limits()
