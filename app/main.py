import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import v1_routes
from app.api import metrics_routes
from app.services.file_service import FileGenerator
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, error_response
from app.utils.logging_config import logger


# ── Sentry (gated on DSN) ────────────────────────────────────────────
def _init_sentry() -> None:
    dsn = settings.sentry_dsn
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        def _before_send(event, hint):
            # Strip request URLs to avoid storing raw video links
            if "request" in event:
                event["request"].pop("url", None)
                event["request"].pop("query_string", None)
                event["request"].pop("data", None)
            return event

        sentry_sdk.init(
            dsn=dsn,
            send_default_pii=False,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[FastApiIntegration()],
            before_send=_before_send,
        )
        logger.info("Sentry initialised.")
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry init.")

_init_sentry()


def _cors_allow_origins() -> list[str]:
    origins: list[str] = []
    for raw in (settings.frontend_url, *settings.cors_extra_origins.split(",")):
        o = raw.strip()
        if o and o not in origins:
            origins.append(o)
    return origins


def _log_startup_security_hints() -> None:
    if settings.debug:
        return
    if settings.metrics_password == "changeme":
        logger.warning(
            "METRICS_PASSWORD is still the default 'changeme'. "
            "Set a strong METRICS_USERNAME / METRICS_PASSWORD before public deployment."
        )


# Cleanup is handled by a dedicated Render cron job (python -m app.cleanup),
# NOT by an in-process asyncio loop. This avoids duplicate cleanup across
# Gunicorn workers and keeps web processes focused on serving requests.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up TranscriptFlow API...")
    _log_startup_security_hints()
    yield
    # Shutdown actions
    logger.info("Shutting down API...")

app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)


# ── Global Exception Handlers ────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """All AppError exceptions are returned as structured JSON."""
    return error_response(exc)


@app.exception_handler(Exception)
async def fallback_error_handler(request: Request, exc: Exception):
    """Catch-all for any unhandled exception — always returns INTERNAL_ERROR."""
    logger.error(f"Unhandled exception: {exc}")
    return error_response(
        AppError(ErrorCode.INTERNAL_ERROR, "An unexpected error occurred.", 500)
    )


# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_routes.router, prefix="/api")
app.include_router(metrics_routes.router)

@app.get("/")
async def root():
    return {"success": True, "message": "TranscriptFlow API is running"}

