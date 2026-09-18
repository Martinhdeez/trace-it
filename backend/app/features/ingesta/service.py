import hashlib
import json
import logging
import os
import threading
import time
import uuid
from contextlib import suppress
from pathlib import Path

from app.common.exceptions import NotFoundError
from app.features.fuentes.service import extract_workbook
from app.features.ingesta.config import Settings
from app.features.ingesta.ocr.local import LocalOCR
from app.features.ingesta.ocr.vision import VisionFallback
from app.features.ingesta.pdf.extractor import extract_pdf
from app.features.ingesta.schemas import REQUIRED_INVOICE_FIELDS, ExtractionResult, ExtractOptions
from app.features.ingesta.store import Store

PIPELINE_VERSION = "invoice-v1.8.0+xlsx-v1.3"
logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(self, settings: Settings, ocr=None, vlm=None):
        self.settings = settings
        self.objects = settings.data_dir / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.store = Store(settings.data_dir / "tracepay.sqlite3")
        self.ocr = ocr or LocalOCR(settings)
        self.vlm = vlm or VisionFallback(settings)
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
        config = {
            "sha": item["sha256"],
            "kind": item["kind"],
            "options": options.model_dump(),
            "pipeline": PIPELINE_VERSION,
            "ocr": self.ocr.signature() if options.ocr else None,
            "dpi": self.settings.ocr_dpi,
            "confidence": self.settings.ocr_min_confidence,
            "cuda": self.settings.ocr_use_cuda,
            "vlm_model": self.settings.vlm_model if options.vlm else None,
            "vlm_endpoint": self.settings.vlm_url if options.vlm else None,
        }
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()

    def extract(self, item, options: ExtractOptions):
        started = time.perf_counter()
        key = self.cache_key(item, options)
        with self.locks[int(key[:8], 16) % len(self.locks)]:
            cached = self.store.cached(key)
            if cached:
                result = ExtractionResult.model_validate(cached)
                result.id, result.file_id = item["id"], item["file_id"]
                result.cache_hit = True
                result.metrics = {
                    **result.metrics,
                    "request_ms": round((time.perf_counter() - started) * 1000, 2),
                    "ocr_calls_this_request": 0,
                    "vlm_calls_this_request": 0,
                }
                self.store.save(result)
                return result
            with self.slots:
                content = (self.objects / item["sha256"]).read_bytes()
                if item["kind"] == "invoice":
                    fields, data, warnings, pages, metrics = extract_pdf(
                        content, options, self.settings, self.ocr, self.vlm
                    )
                    complete = all(fields[k].status == "OBSERVED" for k in REQUIRED_INVOICE_FIELDS)
                    complete = complete and not any(
                        w["code"] in {"OCR_ERROR", "OCR_DISABLED", "OCR_EMPTY", "UNREADABLE_REGION"}
                        for w in warnings
                    )
                else:
                    data, warnings = extract_workbook(content, self.settings)
                    fields, pages = {}, []
                    metrics = {"native_pages": 0, "ocr_calls": 0, "vlm_calls": 0}
                    complete = not any(
                        w["code"]
                        in {
                            "DUPLICATE_CONFLICT",
                            "FIELD_INVALID",
                            "FIELD_AMBIGUOUS",
                            "FIELD_MISSING",
                            "FIELD_UNVERIFIED",
                            "FORMULA_UNEVALUATED",
                            "UNRECOGNIZED_SCHEMA",
                        }
                        for w in warnings
                    )
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                data["provenance"] = {
                    "pipeline_version": PIPELINE_VERSION,
                    "options": options.model_dump(),
                    "ocr_models": self.ocr.signature() if metrics["ocr_calls"] else None,
                    "ocr_dpi": self.settings.ocr_dpi if metrics["ocr_calls"] else None,
                }
                metrics.update(
                    {
                        "extraction_ms": elapsed,
                        "request_ms": elapsed,
                        "ocr_calls_this_request": metrics["ocr_calls"],
                        "vlm_calls_this_request": metrics["vlm_calls"],
                        "bytes": len(content),
                    }
                )
                result = ExtractionResult(
                    **item,
                    status="COMPLETE" if complete else "NEEDS_REVIEW",
                    fields=fields,
                    data=data,
                    warnings=warnings,
                    pages=pages,
                    metrics=metrics,
                    pipeline_version=PIPELINE_VERSION,
                    review={
                        "required": not complete,
                        "action": "CONTINUE" if complete else "HUMAN_REVIEW",
                        "fields": [
                            key for key, field in fields.items() if field.status != "OBSERVED"
                        ],
                        "reasons": sorted({w["code"] for w in warnings}) if not complete else [],
                    },
                )
                transient = any(w["code"] in {"OCR_ERROR", "VLM_ERROR"} for w in warnings)
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
