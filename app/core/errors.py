import json
from enum import Enum
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    TRANSCRIPT_NOT_AVAILABLE = "TRANSCRIPT_NOT_AVAILABLE"
    VIDEO_TOO_LONG = "VIDEO_TOO_LONG"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_EXPIRED = "FILE_EXPIRED"
    CONVERT_FAILED = "CONVERT_FAILED"
    CONVERT_BUSY = "CONVERT_BUSY"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Structured application error that maps to the unified JSON envelope."""

    def __init__(self, code: ErrorCode, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TranscriptFetchError(Exception):
    """
    Upstream transcript failure with a user-safe message.

    Raised by the YouTube/Vimeo services so interfaces (API, Telegram) can map
    failures by type instead of matching on message text.
    """

    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Wraps any payload in the standard success envelope."""
    return {"success": True, **data}


def error_response(error: AppError) -> JSONResponse:
    """Returns a JSONResponse with the standard error envelope."""
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "error": {
                "code": error.code.value,
                "message": error.message,
            },
        },
    )
