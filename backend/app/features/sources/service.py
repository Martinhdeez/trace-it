"""Reference-source services consumed by ingestion and future process workflows."""

from .config import WorkbookLimits
from .excel import extract_workbook as _extract_workbook


def extract_workbook(content: bytes, settings: WorkbookLimits):
    return _extract_workbook(content, settings)
