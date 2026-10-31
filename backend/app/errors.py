"""Structured API errors."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, detail=None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail


def error_payload(code: str, message: str, detail=None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if detail is not None:
        body["error"]["detail"] = detail
    return body


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content=error_payload(exc.code, exc.message, exc.detail)
    )


async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_error",
        503: "service_unavailable",
    }
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(codes.get(exc.status_code, "http_error"), message),
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": ".".join(str(part) for part in err.get("loc", []) if part != "body"),
                "message": err.get("msg", "Invalid value"),
            }
        )
    return JSONResponse(
        status_code=422,
        content=error_payload("validation_error", "Request validation failed", errors),
    )


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
    return JSONResponse(
        status_code=500,
        content=error_payload(
            "internal_error",
            "An unexpected error occurred. Check the server log for details.",
        ),
    )
