class TraceError(Exception):
    """Root of all domain errors. The API turns each one into a JSON response."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(TraceError):
    status_code = 404
    code = "not_found"


class ConflictError(TraceError):
    status_code = 409
    code = "conflict"


class UnauthenticatedError(TraceError):
    status_code = 401
    code = "unauthenticated"


class PermissionDeniedError(TraceError):
    status_code = 403
    code = "permission_denied"
