"""HTTP interface for document ingestion; mountable in the wider application."""

import logging
import zipfile
from typing import Annotated
from xml.etree.ElementTree import ParseError

import pymupdf
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from openpyxl.utils.exceptions import InvalidFileException

from app.common.exceptions import TraceError
from .errors import InvalidDocumentError

from .config import Settings
from .schemas import ExtractionResult, ExtractOptions
from .service import ExtractionService

logger = logging.getLogger(__name__)


def create_router(settings: Settings, service: ExtractionService) -> APIRouter:
    router = APIRouter(tags=["Ingestion"])

    @router.post("/v1/extractions", response_model=ExtractionResult)
    async def extract(
        file: Annotated[
            UploadFile, File(description="Original PDF or XLSX; business fields are read from its contents.")
        ],
        ocr: Annotated[bool, Form(description="Allow local OCR for pages without reliable text.")] = True,
        vlm: Annotated[
            bool, Form(description="Allow the configured vision fallback; proposals remain unverified.")
        ] = False,
    ):
        try:
            item = await run_in_threadpool(service.ingest, file.file, file.filename)
            return await run_in_threadpool(service.extract, item, ExtractOptions(ocr=ocr, vlm=vlm))
        except ValueError as exc:
            raise InvalidDocumentError(str(exc)) from exc
        except (pymupdf.FileDataError, zipfile.BadZipFile, InvalidFileException, ParseError) as exc:
            raise InvalidDocumentError("Corrupt or unsupported document structure") from exc
        except Exception as exc:
            logger.exception("Extraction failed")
            raise TraceError("Internal extraction error; inspect server log and retry") from exc
        finally:
            await file.close()

    @router.get("/v1/extractions/{extraction_id}", response_model=ExtractionResult)
    def get_result(extraction_id: str):
        return service.get_result(extraction_id)

    @router.post("/v1/batches", status_code=202)
    async def submit_batch(
        files: Annotated[
            list[UploadFile],
            File(description="Original PDF or XLSX; business fields are read from its contents."),
        ],
        ocr: Annotated[bool, Form(description="Allow local OCR for pages without reliable text.")] = True,
        vlm: Annotated[
            bool, Form(description="Allow the configured vision fallback; proposals remain unverified.")
        ] = False,
    ):
        try:
            if not 1 <= len(files) <= settings.max_batch_files:
                raise InvalidDocumentError(f"Upload 1-{settings.max_batch_files} files per batch")
            names = [file.filename for file in files]
            if len(names) != len(set(names)):
                raise InvalidDocumentError("Duplicate file names within a batch")
            items = []
            for file in files:
                items.append(await run_in_threadpool(service.ingest, file.file, file.filename))
            options = ExtractOptions(ocr=ocr, vlm=vlm)
            return await run_in_threadpool(service.submit_batch, items, options)
        except ValueError as exc:
            raise InvalidDocumentError(str(exc)) from exc
        finally:
            for file in files:
                await file.close()

    @router.get("/v1/batches/{batch_id}")
    def get_batch(batch_id: str):
        return service.get_batch(batch_id)

    return router
