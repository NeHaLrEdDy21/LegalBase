"""
FastAPI application factory.

Wires together:
  * CORS middleware
  * Rate-limiter middleware
  * Structured JSON logging
  * API v1 routers (chat, documents, health)
  * Global exception handlers
  * Startup / shutdown lifecycle hooks
"""
import logging
import sys

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import chat, documents, health, rules
from app.config.settings import get_settings
from app.middleware.rate_limiter import RateLimiterMiddleware

# ── logging setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── application factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    logging.getLogger().setLevel(settings.log_level.upper())

    app = FastAPI(
        title="Legal Reasoning Chatbot API",
        description=(
            "Neuro-symbolic conversational AI for legal case analysis "
            "powered by RAG + Gemini."
        ),
        version="1.0.0",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limiting ──────────────────────────────────────────────────────────
    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_window=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(rules.router, prefix=prefix)

    # ── Global exception handlers ──────────────────────────────────────────────

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Starting Legal Reasoning Chatbot API…")
        # Eagerly initialise the RAG pipeline to load the embedding model
        # before the first request arrives.
        from app.rag.pipeline import get_rag_pipeline

        get_rag_pipeline()
        logger.info("RAG pipeline ready.")

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Shutting down Legal Reasoning Chatbot API.")

    return app


app = create_app()
