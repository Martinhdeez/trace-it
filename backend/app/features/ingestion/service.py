import hashlib
import logging
import os
import threading
import time
import uuid
from contextlib import suppress
from pathlib import Path

from filelock import FileLock

from app.common.exceptions import NotFoundError
from app.core import events
from app.features.ingestion.cache import file_identity, fingerprint, package_version, reader_usage
from app.features.ingestion.config import Settings
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.ocr.local import LocalOCR
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.pdf.extractor import extract_pdf
from app.features.ingestion.readings import field_readings, full_text
from app.features.ingestion.schemas import ExtractionResult, ExtractOptions
from app.features.ingestion.store import Store
from app.features.sources.excel import extract_workbook

PIPELINE_VERSION = "invoice-v2.2.0+xlsx-v1.3"
logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(self, settings: Settings, ocr=None, vlm=None, judge=None):
        self.settings = settings
        self.objects = settings.data_dir / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.store = Store(settings.data_dir / "tracepay.sqlite3")
        self.ocr = ocr or LocalOCR(settings)
        self.vlm = vlm or VisionFallback(settings)
        self.judge = judge or TextJudge(settings)
        self.locks = [threading.Lock() for _ in range(64)]
        self.stop = threading.Event()
        self.threads = []
        self.slots = threading.BoundedSemaphore(settings.workers)

    def get_result(self, extraction_id: str):
        result = self.store.result(extraction_id)
        if result is None:
            raise NotFoundError("Extraction not found")
        return result

    def get_batch(self, batch_id: str):
        batch = self.store.batch(batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return batch

    def submit_batch(self, items: list[dict], options: ExtractOptions):
        ident = uuid.uuid4().hex
        self.store.submit_batch(ident, items, options, self.settings.max_queued_files)
        return {"id": ident, "files": len(items), "status_url": f"/v1/batches/{ident}"}

    def ingest(self, stream, filename):
        filename = filename or "upload"
        if len(filename) > 255:
            raise ValueError("Filename exceeds 255 characters")
        temp = self.objects / (uuid.uuid4().hex + ".part")
        digest, size, head = hashlib.sha256(), 0, b""
        try:
            with temp.open("wb") as target:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_file_bytes:
                        raise ValueError("File exceeds upload size limit")
                    digest.update(chunk)
                    if not head:
                        head = chunk[:1024]
                    target.write(chunk)
            if not size:
                raise ValueError("Empty file")
            if b"%PDF-" in head:
                kind = "invoice"
            elif head.startswith(b"PK\x03\x04") and Path(filename).suffix.lower() == ".xlsx":
                kind = "workbook"
            else:
                raise ValueError("Supported inputs: PDF and XLSX (legacy XLS is not supported)")
            sha = digest.hexdigest()
            destination = self.objects / sha
            # Publish atomically without replacing an object another worker may be reading.
            with suppress(FileExistsError):
                os.link(temp, destination)
            return {"id": uuid.uuid4().hex, "file_id": filename, "sha256": sha, "kind": kind}
        finally:
            temp.unlink(missing_ok=True)

    def cache_key(self, item, options):
        root = Path(__file__).resolve().parents[2]
        vision = options.vlm is True or (
            options.vlm is None and getattr(self.vlm, "configured", False)
        )
        judge = options.jev is True or (
            options.jev is None and getattr(self.judge, "configured", False)
        )
        shared = [
            "common/extraction.py",
            "common/normalization.py",
            "features/ingestion/readings.py",
            "features/ingestion/schemas.py",
        ]
        invoice = [
            "pdf/extractor.py",
            "pdf/native.py",
            "pdf/invoice.py",
            "pdf/committee.py",
            "pdf/uncertainty.py",
            "pdf/focused.py",
        ]
        if options.ocr:
            invoice += ["ocr/bands.py", "ocr/preprocessing.py", "ocr/local.py"]
        if vision:
            invoice += ["ocr/transcript.py", "ocr/vision.py", "ocr/gemini.py"]
        if judge:
            invoice += ["ocr/judge.py"]
        paths = shared + (
            ["features/ingestion/" + path for path in invoice]
            if item["kind"] == "invoice"
            else ["features/sources/excel.py"]
        )
        config = {
            "sha": item["sha256"],
            "kind": item["kind"],
            "pipeline": PIPELINE_VERSION.split("+")[0 if item["kind"] == "invoice" else 1],
            "cache_schema": 2,
            "implementation": {path: file_identity(root / path) for path in paths},
            "pydantic": package_version("pydantic"),
        }
        if item["kind"] == "workbook":
            config.update(
                openpyxl=package_version("openpyxl"),
                limits={
                    name: getattr(self.settings, name)
                    for name in (
                        "max_excel_cells",
                        "max_excel_rows",
                        "max_excel_cols",
                    )
                },
            )
        else:
            config.update(
                options={
                    "ocr": options.ocr,
                    "vlm": vision,
                    "jev": judge,
                    "verify_fields": sorted(set(options.verify_fields)),
                },
                ocr=self.ocr.signature() if options.ocr else None,
                dpi=self.settings.ocr_dpi,
                confidence=self.settings.ocr_min_confidence,
                cuda=self.settings.ocr_use_cuda if options.ocr else None,
                limits={"pages": self.settings.max_pages, "pixels": self.settings.max_image_pixels},
                pymupdf=package_version("pymupdf"),
                reader_runtime={
                    name: package_version(name)
                    for name in (
                        "rapidocr",
                        "onnxruntime",
                        "onnxruntime-gpu",
                        "opencv-python",
                        "numpy",
                        "pillow",
                    )
                }
                if options.ocr
                else None,
                vision=(
                    self.vlm.signature()
                    if hasattr(self.vlm, "signature")
                    else {
                        "model": self.settings.vlm_model,
                        "endpoint": self.settings.vlm_url,
                        "gemini_model": self.settings.gemini_model,
                        "configured": getattr(self.vlm, "configured", False),
                    }
                )
                if vision
                else None,
                judge=(
                    self.judge.signature()
                    if hasattr(self.judge, "signature")
                    else {
                        "model": self.settings.jev_model,
                        "configured": getattr(self.judge, "configured", False),
                    }
                )
                if judge
                else None,
            )
        return fingerprint(config)

    def extract(self, item, options: ExtractOptions):
        with events.span(
            "extraction",
            kind=item["kind"],
            sha256=item["sha256"],
            extraction_id=item["id"],
            pipeline_version=PIPELINE_VERSION,
            options=options.model_dump(),
        ) as span:
            result = self._extract(item, options)
            provenance = result.data.get("provenance", {})
            span.set(
                cache_hit=result.cache_hit,
                cached_from_extraction_id=provenance.get("cached_from_extraction_id"),
                ocr_models=provenance.get("ocr_models"),
                warnings=len(result.warnings),
                warning_codes=sorted({warning["code"] for warning in result.warnings}),
                **result.metrics,
            )
            return result

    def _extract(self, item, options: ExtractOptions):
        started = time.perf_counter()
        key = self.cache_key(item, options)
        lock_path = self.settings.data_dir / "extraction-locks" / (key + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.locks[int(key[:8], 16) % len(self.locks)], FileLock(str(lock_path), timeout=600):
            cached = self.store.cached(key)
            if cached:
                result = ExtractionResult.model_validate(cached)
                result.data["provenance"] = {
                    **result.data.get("provenance", {}),
                    "cached_from_extraction_id": result.id,
                }
                result.id, result.file_id = item["id"], item["file_id"]
                result.cache_hit = True
                result.metrics = {
                    **result.metrics,
                    "request_ms": round((time.perf_counter() - started) * 1000, 2),
                    "ocr_calls_this_request": 0,
                    "vlm_calls_this_request": 0,
                    "jev_calls_this_request": 0,
                    "ocr_cache_hits_this_request": 0,
                    "vlm_cache_hits_this_request": 0,
                    "jev_cache_hits_this_request": 0,
                }
                self.store.save(result)
                return result
            with self.slots, reader_usage() as usage:
                content = (self.objects / item["sha256"]).read_bytes()
                if item["kind"] == "invoice":
                    fields, data, warnings, pages, metrics = extract_pdf(
                        content, options, self.settings, self.ocr, self.vlm, self.judge
                    )
                else:
                    data, warnings = extract_workbook(content, self.settings)
                    fields, pages = {}, []
                    metrics = {"native_pages": 0, "ocr_calls": 0, "vlm_calls": 0}
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                data["provenance"] = {
                    "cache_key": key,
                    "pipeline_version": PIPELINE_VERSION,
                    "options": options.model_dump(),
                    "ocr_models": self.ocr.signature() if metrics["ocr_calls"] else None,
                    "ocr_dpi": self.settings.ocr_dpi if metrics["ocr_calls"] else None,
                    "visual_model": (
                        self.settings.vlm_model
                        if self.settings.vlm_url and self.settings.vlm_model
                        else self.settings.gemini_model
                    )
                    if metrics["vlm_calls"]
                    else None,
                    "text_judge_model": self.settings.jev_model
                    if metrics.get("jev_calls")
                    else None,
                }
                metrics.update(
                    {
                        "extraction_ms": elapsed,
                        "request_ms": elapsed,
                        "ocr_calls_this_request": metrics["ocr_calls"]
                        - usage.get("ocr_cache_hits", 0),
                        "vlm_calls_this_request": usage.get("vlm_requests", 0)
                        if isinstance(self.vlm, VisionFallback)
                        else metrics["vlm_calls"],
                        "jev_calls_this_request": usage.get("jev_requests", 0)
                        if isinstance(self.judge, TextJudge)
                        else metrics.get("jev_calls", 0),
                        **{
                            name + "_cache_hits_this_request": usage.get(name + "_cache_hits", 0)
                            for name in ("ocr", "vlm", "jev")
                        },
                        "bytes": len(content),
                    }
                )
                result = ExtractionResult(
                    **item,
                    fields=field_readings(fields, data),
                    text=full_text(data),
                    data=data,
                    warnings=warnings,
                    pages=pages,
                    metrics=metrics,
                    pipeline_version=PIPELINE_VERSION,
                )
                transient = any(
                    w["code"] in {"OCR_ERROR", "VLM_ERROR", "JEV_ERROR", "FOCUSED_READER_ERROR"}
                    for w in warnings
                )
                self.store.save(result, None if transient else key)
                return result

    def start(self):
        self.store.recover()
        for i in range(self.settings.workers):
            thread = threading.Thread(target=self._worker, name=f"extraction-{i}", daemon=True)
            self.threads.append(thread)
            thread.start()

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join()

    def _worker(self):
        while not self.stop.is_set():
            job = self.store.claim()
            if not job:
                self.stop.wait(0.2)
                continue
            item = {k: job[k] for k in ("id", "file_id", "sha256", "kind")}
            try:
                result = self.extract(item, ExtractOptions.model_validate_json(job["options"]))
                self.store.finish(job["id"], result.id)
            except Exception as exc:
                logger.exception("Extraction job %s failed", job["id"])
                self.store.finish(
                    job["id"], error=f"{type(exc).__name__}: extraction failed; inspect server log"
                )
