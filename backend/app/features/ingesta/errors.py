from app.common.exceptions import TraceError


class InvalidDocumentError(TraceError):
    status_code = 422
    code = "invalid_document"
