"""Process-facing ingestion routes composed into the main dev application."""

import logging
from typing import Annotated

import pymupdf
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.common.exceptions import TraceError
from app.core.database import Session
from app.features.users.dependencies import CurrentUser

from . import process_service
from .errors import InvalidDocumentError
from .runtime import current_service
from .schemas import ExtractionResult, ExtractOptions
from .service import ExtractionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingestion"])
Service = Annotated[ExtractionService, Depends(current_service)]


class DocumentUpload(BaseModel):
    instance_id: int
    process_id: int
    name: str
    file_hash: str
    status: str
    created: bool
    extraction: ExtractionResult


@router.post(
    "/processes/{process_id}/files",
    status_code=201,
    operation_id="uploadProcessDocument",
    summary="Store a PDF and its reading evidence as an instance of a process",
    response_model=DocumentUpload,
)
async def upload_document(
    process_id: int,
    session: Session,
    user: CurrentUser,
    service: Service,
    file: Annotated[UploadFile, File()],
    ocr: Annotated[bool, Form()] = True,
    vlm: Annotated[bool | None, Form()] = None,
    jev: Annotated[bool | None, Form()] = None,
):
    try:
        await process_service.require_process(session, process_id)
        try:
            item = await run_in_threadpool(service.ingest, file.file, file.filename)
            if item["kind"] != "invoice":
                raise InvalidDocumentError(
                    "Process documents must be PDF; use /v1/extractions to inspect a workbook"
                )
            result = await run_in_threadpool(
                service.extract, item, ExtractOptions(ocr=ocr, vlm=vlm, jev=jev)
            )
        except (ValueError, pymupdf.FileDataError) as exc:
            raise InvalidDocumentError("Invalid or unsupported PDF document") from exc
        except TraceError:
            raise
        except Exception as exc:
            logger.exception("Document extraction failed")
            raise TraceError("Document extraction failed; inspect server logs") from exc
        content = await run_in_threadpool((service.objects / item["sha256"]).read_bytes)
        return await process_service.attach_document(session, process_id, user.id, content, result)
    finally:
        await file.close()


@router.get(
    "/instances/{instance_id}/document",
    operation_id="getInstanceDocument",
    summary="Read persisted document evidence from PostgreSQL",
    response_model=ExtractionResult,
)
async def get_document(instance_id: int, session: Session, user: CurrentUser):
    return await process_service.document_result(session, instance_id)
