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


class NotImplementedYetError(TraceError):
    """A contract that exists but whose owner has not filled it in yet."""

    status_code = 501
    code = "not_implemented"


class PermissionDeniedError(TraceError):
    status_code = 403
    code = "permission_denied"
