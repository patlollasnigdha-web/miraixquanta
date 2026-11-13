"""
MIRAI — API Exception Handlers (M15)
Standardized error mapping, status codes, and security sanitization.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.utils.logger import get_logger
from src.paper_trading.paper_trading_schemas import InvalidSessionStateError
from src.assistant.ollama_client import OllamaServiceUnavailableError
from src.monitoring.metrics_collector import default_metrics

logger = get_logger("APIExceptionHandler")


async def session_state_exception_handler(request: Request, exc: InvalidSessionStateError) -> JSONResponse:
    """Handles illegal paper trading session lifecycle transitions."""
    default_metrics.record_error(endpoint=request.url.path, error_msg=str(exc), status_code=status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error_type": "InvalidSessionStateError",
            "message": str(exc),
            "path": request.url.path,
        },
    )


async def ollama_unavailable_exception_handler(request: Request, exc: OllamaServiceUnavailableError) -> JSONResponse:
    """Handles Ollama local daemon downtime without failing backend."""
    default_metrics.record_error(endpoint=request.url.path, error_msg=str(exc), status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "error_type": "OllamaServiceUnavailable",
            "message": str(exc),
            "path": request.url.path,
        },
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handles validation and calculation parameter errors."""
    default_metrics.record_error(endpoint=request.url.path, error_msg=str(exc), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_type": "ValidationError",
            "message": str(exc),
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global catch-all exception handler avoiding credential or internal path leakage."""
    logger.error("Unhandled API exception on %s: %s", request.url.path, exc, exc_info=True)
    default_metrics.record_error(endpoint=request.url.path, error_msg=str(exc), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_type": "InternalServerError",
            "message": "An internal system error occurred while processing your request.",
            "path": request.url.path,
        },
    )
