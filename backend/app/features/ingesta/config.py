import os
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("TRACEPAY_DATA_DIR", str(REPOSITORY_ROOT / ".data")))
    )
    model_dir: Path = field(
        default_factory=lambda: Path(os.getenv("TRACEPAY_MODEL_DIR", str(REPOSITORY_ROOT / ".models")))
    )
    max_file_bytes: int = 25 * 1024 * 1024
    max_pages: int = 40
    max_image_pixels: int = 18_000_000
    max_excel_cells: int = 500_000
    max_excel_rows: int = 25_000
    max_excel_cols: int = 100
    workers: int = field(default_factory=lambda: int(os.getenv("TRACEPAY_WORKERS", "2")))
    ocr_threads: int = field(default_factory=lambda: int(os.getenv("TRACEPAY_OCR_THREADS", "4")))
    ocr_use_cuda: bool = field(default_factory=lambda: os.getenv("TRACEPAY_OCR_CUDA", "0") == "1")
    ocr_dpi: int = 240
    ocr_min_confidence: float = 0.90
    vlm_url: str | None = field(default_factory=lambda: os.getenv("TRACEPAY_VLM_URL"))
    vlm_model: str | None = field(default_factory=lambda: os.getenv("TRACEPAY_VLM_MODEL"))
    vlm_api_key: str | None = field(default_factory=lambda: os.getenv("TRACEPAY_VLM_API_KEY"))
    vlm_timeout: float = 60.0
    max_batch_files: int = 100
    max_queued_files: int = 1000

    def __post_init__(self):
        if not 1 <= self.workers <= 8 or not 1 <= self.ocr_threads <= 16:
            raise ValueError("Use 1-8 workers and 1-16 OCR threads to bound memory and CPU use")
