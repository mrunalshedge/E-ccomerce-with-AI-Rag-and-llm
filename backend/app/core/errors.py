"""Domain errors raised by services; ``main.py`` maps them to HTTP responses.

Keeping services free of ``HTTPException`` lets them be reused from scripts, workers and
the AI agent later.
"""


class AppError(Exception):
    status_code: int = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PermissionDeniedError(AppError):
    status_code = 403


class ServiceUnavailableError(AppError):
    status_code = 503
