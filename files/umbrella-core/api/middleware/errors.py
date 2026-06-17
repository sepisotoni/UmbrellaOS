"""
api/middleware/errors.py — Global error handling and standardized responses.

Provides:
- Custom exception classes for consistent error handling
- Error response schemas
- Exception handlers for FastAPI
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    success: bool = False
    error: str
    code: str
    status: int
    timestamp: str
    path: Optional[str] = None
    details: Optional[Any] = None


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str, status_code: int = 400, details: Any = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class PermissionDeniedException(AppException):
    """User lacks required permission."""
    def __init__(self, message: str = "Insufficient permissions", details: Any = None):
        super().__init__(message, "PERMISSION_DENIED", 403, details)


class ResourceNotFoundException(AppException):
    """Requested resource not found."""
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, "NOT_FOUND", 404)


class ValidationException(AppException):
    """Input validation failed."""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "VALIDATION_ERROR", 422, details)


class UnauthorizedException(AppException):
    """Authentication failed."""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ConflictException(AppException):
    """Resource conflict (duplicate, state mismatch, etc)."""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "CONFLICT", 409, details)


class RateLimitException(AppException):
    """Rate limit exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message, "RATE_LIMIT", 429, {"retry_after": retry_after})


def register_error_handlers(app: FastAPI) -> None:
    """Register global error handlers for FastAPI."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle custom application exceptions."""
        error_response = ErrorResponse(
            success=False,
            error=exc.message,
            code=exc.code,
            status=exc.status_code,
            timestamp=datetime.utcnow().isoformat(),
            path=str(request.url.path),
            details=exc.details
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(error_response)
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="Internal server error",
            code="INTERNAL_ERROR",
            status=500,
            timestamp=datetime.utcnow().isoformat(),
            path=str(request.url.path),
            details=str(exc) if str(exc) else None
        )
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(error_response)
        )


class SuccessResponse(BaseModel):
    """Standardized success response format."""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    timestamp: str
