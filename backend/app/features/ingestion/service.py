import hashlib
import json
import logging
import os
import re
import threading
import time
import unicodedata
import uuid
from collections import OrderedDict
from contextlib import contextmanager, suppress
from copy import copy
from pathlib import Path

from filelock import FileLock

from app.common.exceptions import NotFoundError
from app.core import events
from app.features.ingestion.cache import file_identity, fingerprint, package_version, reader_usage
from app.features.ingestion.config import Settings
from app.features.ingestion.ocr.budget import acquired, extraction_budget, remaining
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.ocr.local import LocalOCR
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.pdf.extractor import extract_pdf
from app.features.ingestion.pdf.schema import extract_schema_pdf
from app.features.ingestion.readings import field_readings, full_text
from app.features.ingestion.schema_fields import SchemaFieldReader, normalize_schema_value
from app.features.ingestion.schemas import ExtractionResult, ExtractOptions, FieldReading
from app.features.ingestion.store import Store
from app.features.sources.excel import extract_workbook

PIPELINE_VERSION = "invoice-v2.3.0+xlsx-v1.3"
logger = logging.getLogger(__name__)


def _used_visual_models(fields, data):
    identities = set()
    locators = [line.get("id", "") for line in data.get("lines", [])]
    locators.extend(
        candidate.evidence.locator
        for field in fields.values()
        for candidate in field.candidates
        if candidate.evidence.method == "vlm"
    )
    for locator in locators:
        for provider, model in re.findall(r"(?:^|:)visual:([^:]+):([^:]+):", locator):
            if provider not in {"focus", "focus_high"}:
                identities.add((provider, model))
    return [{"provider": provider, "model": model} for provider, model in sorted(identities)]


class ExtractionService:
    def __init__(self, settings: Settings, ocr=None, vlm=None, judge=None, field_reader=None):
        self.settings = settings
        self.objects = settings.data_dir / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.store = Store(settings.data_dir / "tracepay.sqlite3")
        self.ocr = ocr or LocalOCR(settings)
        self.vlm = vlm or VisionFallback(settings)
        self.judge = judge or TextJudge(settings)
        self.field_reader = field_reader or SchemaFieldReader(settings)
        self.locks = [threading.Lock() for _ in range(64)]
        self.stop = threading.Event()
        self.threads = []
        self.slots = threading.BoundedSemaphore(settings.workers)
        self.configured_services = OrderedDict()
        self.configuration_lock = threading.Lock()
        self.execution_hash = None

    def configured(self, config):
        """Request-local readers/settings, sharing storage, locks and worker limits."""
        from app.features.processes.execution import ingestion_settings

        key = fingerprint(config.model_dump(mode="json", exclude={"agents", "preset"}))
        with self.configuration_lock:
            if key in self.configured_services:
                self.configured_services.move_to_end(key)
                return self.configured_services[key]
            service = copy(self)
            service.settings = ingestion_settings(config, self.settings)
            if (
                service.settings.model_dir != self.settings.model_dir
                or service.settings.verification_model_dir
                != (self.settings.verification_model_dir or self.settings.model_dir / "verify")
            ):
                service.ocr = LocalOCR(service.settings)
            service.vlm = VisionFallback(
                service.settings,
                http=self.vlm.http if isinstance(self.vlm, VisionFallback) else None,
            )
            service.judge = TextJudge(
                service.settings,
                http=self.judge.http if isinstance(self.judge, TextJudge) else None,
            )
            service.field_reader = SchemaFieldReader(
                service.settings,
                http=self.field_reader.http
                if isinstance(self.field_reader, SchemaFieldReader)
                else None,
            )
            service.execution_hash = key
            self.configured_services[key] = service
            # Eviction never invalidates a reader already held by an in-flight operation.
            if len(self.configured_services) > 8:
                self.configured_services.popitem(last=False)
            return service

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
        options = options.normalized(self.settings)
        ident = uuid.uuid4().hex
        self.store.submit_batch(ident, items, options, self.settings.max_queued_files)
        return {"id": ident, "files": len(items), "status_url": f"/v1/batches/{ident}"}

    def ingest(self, stream, filename):
        # macOS hands a dropped file its name decomposed (NFD): "á" as "a" + accent. Compose
        # it, or the same invoice gets a second instance under a name that only looks equal.
        filename = unicodedata.normalize("NFC", filename or "upload")
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
        options = options.normalized(self.settings)
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
            "features/ingestion/schema_fields.py",
            "features/ingestion/config.py",
        ]
        invoice = [
            "pdf/international.py",
            "pdf/visual_risk.py",
            "pdf/extractor.py",
            "pdf/native.py",
            "pdf/layout.py",
            "pdf/invoice.py",
            "pdf/committee.py",
            "pdf/uncertainty.py",
            "pdf/focused.py",
            "pdf/schema.py",
        ]
        if options.ocr:
            invoice += ["ocr/bands.py", "ocr/preprocessing.py", "ocr/local.py"]
        if vision:
            invoice += [
                "ocr/transcript.py",
                "ocr/vision.py",
                "ocr/gemini.py",
                "ocr/journal.py",
                "ocr/errors.py",
                "ocr/budget.py",
                "ocr/http.py",
                "ocr/pricing.py",
            ]
        if judge:
            invoice += [
                "ocr/judge.py",
                "ocr/journal.py",
                "ocr/errors.py",
                "ocr/budget.py",
                "ocr/http.py",
                "ocr/pricing.py",
            ]
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
                    "mode": options.mode,
                    "ocr": options.ocr,
                    "secondary_ocr": options.secondary_ocr,
                    "focused_verification": options.focused_verification,
                    "source_verification": options.source_verification,
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
            if self.execution_hash is not None:
                config["execution_hash"] = self.execution_hash
        return fingerprint(config)

    def _schema_mapper_signature(self, options):
        if (
            options.mode == "local"
            or options.vlm is False
            or not getattr(self.field_reader, "configured", False)
            or not hasattr(self.field_reader, "signature")
        ):
            return None
        return self.field_reader.signature()

    def extract(self, item, options: ExtractOptions):
        options = options.normalized(self.settings)
        with (
            extraction_budget(self.settings.extraction_timeout),
            events.span(
                "extraction",
                kind=item["kind"],
                sha256=item["sha256"],
                extraction_id=item["id"],
                pipeline_version=PIPELINE_VERSION,
                options=options.model_dump(),
                execution_hash=self.execution_hash,
            ) as span,
        ):
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
        with (
            acquired(self.locks[int(key[:8], 16) % len(self.locks)]),
            FileLock(str(lock_path), timeout=remaining(600)),
        ):
            cached = not self.settings.ocr_force_recompute and self.store.cached(key)
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
                    "worker_wait_ms": 0,
                    "vlm_calls_this_request": 0,
                    "jev_calls_this_request": 0,
                    "ocr_cache_hits_this_request": 0,
                    "vlm_cache_hits_this_request": 0,
                    "jev_cache_hits_this_request": 0,
                }
                self.store.save(result)
                return result
            with self.worker_slot() as worker_wait_ms, reader_usage() as usage:
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
                visual_models = _used_visual_models(fields, data)
                judgment = data.get("committee", {}).get("text_judge", {})
                data["provenance"] = {
                    "cache_key": key,
                    "execution_hash": self.execution_hash,
                    "pipeline_version": PIPELINE_VERSION,
                    "options": options.model_dump(),
                    "ocr_models": self.ocr.signature() if metrics["ocr_calls"] else None,
                    "ocr_dpi": self.settings.ocr_dpi if metrics["ocr_calls"] else None,
                    "visual_model": visual_models[0]["model"] if len(visual_models) == 1 else None,
                    "visual_models": visual_models,
                    "visual_chain": (
                        self.vlm.signature().get("chain")
                        if metrics["vlm_calls"] and hasattr(self.vlm, "signature")
                        else None
                    ),
                    "text_judge_model": judgment.get("model"),
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
                        "worker_wait_ms": worker_wait_ms,
                    }
                )
                result = ExtractionResult(
                    **item,
                    fields=field_readings(fields, data, require_verified=options.mode == "api"),
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

    def extract_schema(self, item, options, plan, fields=None, base=None):
        """A schema-specific cache never replaces the invoice pipeline's observations."""
        options = options.normalized(self.settings)
        fields = plan.fields if fields is None else fields
        config = {
            "reader": self.cache_key(item, options),
            "plan": plan.field_fingerprint,
            "fields": [field.model_dump(mode="json") for field in fields],
            "filename": item["file_id"],
            "schema_mapper": self._schema_mapper_signature(options),
            "base": {
                "fields": {name: field.model_dump() for name, field in base.fields.items()},
                "lines": base.data.get("lines", []),
                "warnings": base.warnings,
            }
            if base
            else None,
        }
        key = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        started = time.perf_counter()
        with (
            extraction_budget(self.settings.extraction_timeout),
            events.span(
                "extraction",
                adapter="schema",
                extraction_id=item["id"],
                plan_hash=plan.fingerprint,
                execution_hash=self.execution_hash,
                fields=[field.name for field in fields],
            ) as span,
            acquired(self.locks[int(key[:8], 16) % len(self.locks)]),
        ):
            cached = not self.settings.ocr_force_recompute and self.store.cached(key)
            if cached:
                result = ExtractionResult.model_validate(cached)
                previous_id = result.id
                result.id, result.file_id = item["id"], item["file_id"]
                result.cache_hit = True
                result.data["provenance"]["cached_from_extraction_id"] = previous_id
                result.data["provenance"]["plan_hash"] = plan.fingerprint
                result.data["provenance"].update(
                    execution_hash=self.execution_hash,
                    cache_key=key,
                    schema_mapper=config["schema_mapper"],
                )
                result.data["extraction_plan"] = {
                    **plan.model_dump(mode="json"),
                    "fingerprint": plan.fingerprint,
                }
                if base:
                    result.data["base_extraction_id"] = base.id
                result.warnings = [
                    warning
                    for warning in result.warnings
                    if warning["code"]
                    not in {"SCHEMA_INVALID_RULE_CODE", "SCHEMA_UNDECLARED_SYMBOL"}
                ] + plan.warnings
                result.metrics.update(
                    request_ms=round((time.perf_counter() - started) * 1000, 2),
                    ocr_calls_this_request=0,
                    worker_wait_ms=0,
                    vlm_calls_this_request=0,
                    jev_calls_this_request=0,
                    schema_calls_this_request=0,
                    ocr_cache_hits_this_request=0,
                    vlm_cache_hits_this_request=0,
                    jev_cache_hits_this_request=0,
                    schema_cache_hits_this_request=0,
                )
                self.store.save(result)
                span.set(cache_hit=True, cached_from_extraction_id=previous_id)
                return result
            with self.worker_slot() as worker_wait_ms, reader_usage() as usage:
                readings, data, warnings, pages, metrics = extract_schema_pdf(
                    (self.objects / item["sha256"]).read_bytes(),
                    options,
                    self.settings,
                    self.ocr,
                    self.vlm,
                    self.field_reader,
                    fields,
                    base,
                )
                visual_models = _used_visual_models(readings, data)
                text = full_text(data)
                for field in fields:
                    if field.source != "document":
                        value = {"filename": item["file_id"], "text": text}.get(field.source)
                        if value is not None and field.type.lower() not in {"text", "string"}:
                            try:
                                value = normalize_schema_value(value, field.type.lower())
                            except ValueError:
                                value = None
                                warnings.append(
                                    {"code": "SCHEMA_INVALID_METADATA", "field": field.name}
                                )
                        readings[field.name] = FieldReading(
                            value=value,
                            verification="metadata" if value is not None else "missing",
                            selected_by=field.source if value is not None else None,
                        )
                schema_data = {
                    "extraction_plan": {
                        **plan.model_dump(mode="json"),
                        "fingerprint": plan.fingerprint,
                    },
                    "schema_fields": {
                        name: reading.model_dump() for name, reading in readings.items()
                    },
                    "provenance": {
                        "cache_key": key,
                        "execution_hash": self.execution_hash,
                        "schema_mapper": config["schema_mapper"],
                        "pipeline_version": plan.version,
                        "options": options.model_dump(),
                        "visual_model": (
                            visual_models[0]["model"] if len(visual_models) == 1 else None
                        ),
                        "visual_models": visual_models,
                        "visual_chain": (
                            self.vlm.signature().get("chain")
                            if metrics["vlm_calls"] and hasattr(self.vlm, "signature")
                            else None
                        ),
                        "plan_hash": plan.fingerprint,
                    },
                }
                if base:
                    schema_data["base_extraction_id"] = base.id
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                metrics.update(
                    extraction_ms=elapsed,
                    worker_wait_ms=worker_wait_ms,
                    request_ms=elapsed,
                    ocr_calls_this_request=metrics["ocr_calls"] - usage.get("ocr_cache_hits", 0),
                    vlm_calls_this_request=(
                        usage.get("vlm_requests", 0)
                        if isinstance(self.vlm, VisionFallback)
                        else metrics["vlm_calls"]
                    ),
                    jev_calls_this_request=0,
                    schema_calls=usage.get("schema_journal_calls", 0),
                    schema_calls_this_request=usage.get("schema_requests", 0),
                    **{
                        name + "_cache_hits_this_request": usage.get(name + "_cache_hits", 0)
                        for name in ("ocr", "vlm", "jev", "schema")
                    },
                )
                result = ExtractionResult(
                    **item,
                    fields={**readings, **(base.fields if base else {})},
                    text=text,
                    data={**(base.data if base else {}), **data, **schema_data},
                    warnings=[*(base.warnings if base else []), *warnings, *plan.warnings],
                    pages=pages,
                    metrics=metrics,
                    pipeline_version=(base.pipeline_version + "+" if base else "") + plan.version,
                )
                transient = any(w["code"].endswith("_ERROR") for w in result.warnings)
                self.store.save(result, None if transient else key)
                span.set(cache_hit=False, warnings=len(result.warnings), **metrics)
                return result

    @contextmanager
    def worker_slot(self):
        queued = time.perf_counter()
        with acquired(self.slots):
            wait_ms = round((time.perf_counter() - queued) * 1000, 2)
            if events.current() is not None:
                events.current().set(worker_wait_ms=wait_ms)
            yield wait_ms

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
        for reader in (self.vlm, self.judge, self.field_reader):
            if isinstance(reader, (VisionFallback, TextJudge, SchemaFieldReader)):
                reader.http.close()

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
