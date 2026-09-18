from typing import Protocol


class WorkbookLimits(Protocol):
    """Structural limits supplied by the caller; no dependency on ingestion."""

    max_excel_rows: int
    max_excel_cols: int
    max_excel_cells: int
