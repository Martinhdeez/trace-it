"""HTTP interface for document ingestion; mountable in the wider application."""

import logging
import zipfile
from typing import Annotated, Literal
from xml.etree.ElementTree import ParseError

import pymupdf
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from openpyxl.utils.exceptions import InvalidFileException

from app.common.exceptions import TraceError

from .config import Settings
from .errors import InvalidDocumentError
from .runtime import current_service
from .schemas import CriticalField, ExtractionResult, ExtractOptions
from .service import ExtractionService

logger = logging.getLogger(__name__)


def create_router(
    settings: Settings | None = None, service: ExtractionService | None = None
) -> APIRouter:
    router = APIRouter(tags=["ingestion"])

    @router.get("/v1/ocr/config", operation_id="getOcrConfig")
    def ocr_config(request: Request):
        return (service or current_service(request)).settings.summary()

    @router.post("/v1/extractions", response_model=ExtractionResult, operation_id="extractDocument")
    async def extract(
        request: Request,
        file: Annotated[
            UploadFile,
            File(description="PDF, JPG, PNG, HTML or XLSX; fields are read from the contents."),
        ],
        ocr: Annotated[
            bool, Form(description="Allow local OCR for pages without reliable text.")
        ] = True,
        vlm: Annotated[
            bool | None,
            Form(
                description="Use visual reading when needed; omitted enables configured providers."
            ),
        ] = None,
        jev: Annotated[
            bool | None,
            Form(description="Allow Jev recommendations; omitted enables the configured judge."),
        ] = None,
        verify_fields: Annotated[list[CriticalField] | None, Form()] = None,
        mode: Annotated[Literal["local", "api", "hybrid"] | None, Form()] = None,
    ):
        engine = service or current_service(request)
        try:
            item = await run_in_threadpool(engine.ingest, file.file, file.filename)
            return await run_in_threadpool(
                engine.extract,
                item,
                ExtractOptions(
                    mode=mode, ocr=ocr, vlm=vlm, jev=jev, verify_fields=verify_fields or []
                ),
            )
        except ValueError as exc:
            raise InvalidDocumentError(str(exc)) from exc
        except (pymupdf.FileDataError, zipfile.BadZipFile, InvalidFileException, ParseError) as exc:
            raise InvalidDocumentError("Corrupt or unsupported document structure") from exc
        except TraceError:
            raise
        except Exception as exc:
            logger.exception("Extraction failed")
            raise TraceError("Internal extraction error; inspect server log and retry") from exc
        finally:
            await file.close()

    @router.get(
        "/v1/extractions/{extraction_id}",
        response_model=ExtractionResult,
        operation_id="getDocumentExtraction",
    )
    def get_result(extraction_id: str, request: Request):
        return (service or current_service(request)).get_result(extraction_id)

    @router.post("/v1/batches", status_code=202, operation_id="submitDocumentBatch")
    async def submit_batch(
        request: Request,
        files: Annotated[
            list[UploadFile],
            File(description="PDF, JPG, PNG, HTML or XLSX; fields are read from the contents."),
        ],
        ocr: Annotated[
            bool, Form(description="Allow local OCR for pages without reliable text.")
        ] = True,
        vlm: Annotated[
            bool | None,
            Form(
                description="Use visual reading when needed; omitted enables configured providers."
            ),
        ] = None,
        jev: Annotated[
            bool | None,
            Form(description="Allow Jev recommendations; omitted enables the configured judge."),
        ] = None,
        verify_fields: Annotated[list[CriticalField] | None, Form()] = None,
        mode: Annotated[Literal["local", "api", "hybrid"] | None, Form()] = None,
    ):
        engine = service or current_service(request)
        try:
            if not 1 <= len(files) <= engine.settings.max_batch_files:
                raise InvalidDocumentError(
                    f"Upload 1-{engine.settings.max_batch_files} files per batch"
                )
            names = [file.filename for file in files]
            if len(names) != len(set(names)):
                raise InvalidDocumentError("Duplicate file names within a batch")
            items = []
            for file in files:
                items.append(await run_in_threadpool(engine.ingest, file.file, file.filename))
            options = ExtractOptions(
                mode=mode, ocr=ocr, vlm=vlm, jev=jev, verify_fields=verify_fields or []
            )
            return await run_in_threadpool(engine.submit_batch, items, options)
        except ValueError as exc:
            raise InvalidDocumentError(str(exc)) from exc
        finally:
            for file in files:
                await file.close()

    @router.get("/v1/batches/{batch_id}", operation_id="getDocumentBatch")
    def get_batch(batch_id: str, request: Request):
        return (service or current_service(request)).get_batch(batch_id)

    return router
