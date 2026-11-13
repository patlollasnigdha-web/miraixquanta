"""
MIRAI — FastAPI Application (M15)
Main application entry point configuring middleware, routers, exception handlers,
and metrics instrumentation.
"""

from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.utils.logger import get_logger
from src.api.config import get_api_settings
from src.api.exception_handlers import (
    session_state_exception_handler,
    ollama_unavailable_exception_handler,
    value_error_handler,
    generic_exception_handler,
)
from src.paper_trading.paper_trading_schemas import InvalidSessionStateError
from src.assistant.ollama_client import OllamaServiceUnavailableError
from src.monitoring.metrics_collector import default_metrics
from src.api.routes import (
    health_router,
    market_data_router,
    stock_intelligence_router,
    predictions_router,
    strategies_router,
    decisions_router,
    portfolio_router,
    risk_router,
    execution_router,
    backtesting_router,
    paper_trading_router,
    assistant_router,
    monitoring_router,
)

logger = get_logger("MIRAI-API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("MIRAI FastAPI Backend initialized successfully.")
    default_metrics.set_gauge("app_status", 1.0)
    yield
    logger.info("MIRAI FastAPI Backend shutting down.")
    default_metrics.set_gauge("app_status", 0.0)


def create_app() -> FastAPI:
    """Factory function for FastAPI application instance."""
    settings = get_api_settings()

    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
        lifespan=lifespan,
    )

    # 1. CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Timing & Observability Middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        t0 = time.perf_counter()
        default_metrics.increment_counter("api_requests_total")
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            default_metrics.record_timing("api_request_duration_ms", elapsed_ms, {"path": request.url.path})
            response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
            return response
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            default_metrics.record_timing("api_request_duration_ms", elapsed_ms, {"path": request.url.path, "error": "true"})
            raise e

    # 3. Exception Handlers
    app.add_exception_handler(InvalidSessionStateError, session_state_exception_handler)
    app.add_exception_handler(OllamaServiceUnavailableError, ollama_unavailable_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 4. Register Routers
    api_prefix = settings.prefix
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(market_data_router, prefix=api_prefix)
    app.include_router(stock_intelligence_router, prefix=api_prefix)
    app.include_router(predictions_router, prefix=api_prefix)
    app.include_router(strategies_router, prefix=api_prefix)
    app.include_router(decisions_router, prefix=api_prefix)
    app.include_router(portfolio_router, prefix=api_prefix)
    app.include_router(risk_router, prefix=api_prefix)
    app.include_router(execution_router, prefix=api_prefix)
    app.include_router(backtesting_router, prefix=api_prefix)
    app.include_router(paper_trading_router, prefix=api_prefix)
    app.include_router(assistant_router, prefix=api_prefix)
    app.include_router(monitoring_router, prefix=api_prefix)

    # Root probe
    @app.get("/", tags=["Root"])
    def root():
        return {
            "name": settings.title,
            "version": settings.version,
            "status": "ONLINE",
            "docs_url": "/docs",
            "api_prefix": api_prefix,
        }

    return app


app = create_app()
