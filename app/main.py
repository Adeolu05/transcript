import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import metrics_routes, v1_routes
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, error_response
from app.services.file_service import FileGenerator, TEMP_DIR
from app.services.transcript_cache_service import prune_transcript_cache
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
    """
    Build the CORS allowlist from FRONTEND_URL + CORS_EXTRA_ORIGINS.

    Also adds the localhost ↔ 127.0.0.1 twin for the primary origin so local
    dev works whether the browser bar uses either host (browsers treat them
    as different origins for CORS).
    """
    origins: list[str] = []

    def _add(o: str) -> None:
        o = o.strip().rstrip("/")
        if o and o not in origins:
            origins.append(o)

    for raw in (settings.frontend_url, *settings.cors_extra_origins.split(",")):
        _add(raw)

    # Localhost / loopback twin (dev convenience)
    for o in list(origins):
        if "://localhost" in o:
            _add(o.replace("://localhost", "://127.0.0.1", 1))
        elif "://127.0.0.1" in o:
            _add(o.replace("://127.0.0.1", "://localhost", 1))

    return origins


def _log_startup_security_hints() -> None:
    if settings.debug:
        return
    if settings.metrics_password == "changeme":
        logger.warning(
            "METRICS_PASSWORD is still the default 'changeme'. "
            "Set a strong METRICS_USERNAME / METRICS_PASSWORD before public deployment."
        )


async def _cleanup_loop() -> None:
    """
    Primary temp-file cleanup path for multi-service PaaS (e.g. Render).

    Cron jobs run in a separate filesystem and cannot see API-local /tmp.
    Storing files under data/tmp + in-process cleanup keeps TTL enforcement
    on the same disk as writers. Multiple Gunicorn workers may each run this
    loop; delete-if-old is idempotent.
    """
    interval = max(60, int(settings.cleanup_interval_seconds))
    while True:
        try:
            deleted = await asyncio.to_thread(
                FileGenerator.cleanup_old_files, settings.file_ttl_hours
            )
            if deleted:
                logger.info("In-process cleanup deleted %s file(s) from %s", deleted, TEMP_DIR)
            pruned = await asyncio.to_thread(prune_transcript_cache)
            if pruned:
                logger.info("In-process cleanup pruned %s expired cache entr(ies)", pruned)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("In-process cleanup error: %s", e)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up TranscriptFlow API...")
    logger.info("File storage directory: %s", TEMP_DIR)
    _log_startup_security_hints()

    cleanup_task: asyncio.Task | None = None
    if settings.in_process_cleanup_enabled:
        cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info(
            "In-process file cleanup enabled (every %ss, TTL %sh)",
            settings.cleanup_interval_seconds,
            settings.file_ttl_hours,
        )

    yield

    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
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
    logger.error("Unhandled exception: %s", exc)
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
