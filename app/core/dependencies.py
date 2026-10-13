from fastapi import Request

from app.services.rate_limit_service import check_rate_limit
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.services.metadata_service import MetadataService
from app.services.telemetry_service import hash_identifier
from app.utils.logging_config import logger


def _extract_client_ip(request: Request) -> str:
    """
    Securely extracts the real client IP.

    If trusted_proxy_count == 0 (default / direct exposure), we IGNORE
    X-Forwarded-For entirely and use the raw socket IP. This prevents
    spoofing when there is no trusted reverse proxy in front.

    If trusted_proxy_count >= 1, we read X-Forwarded-For from the RIGHT
    side of the chain (the proxy-appended entries), skipping exactly
    (trusted_proxy_count - 1) proxy hops to land on the real client IP.
    """
    trusted = settings.trusted_proxy_count

    if trusted == 0:
        ip = request.client.host if request.client else "unknown"
        logger.debug("IP extraction: source=tcp, trusted_proxies=0")
        return ip

    xff = request.headers.get("X-Forwarded-For", "")
    if not xff:
        ip = request.client.host if request.client else "unknown"
        logger.debug("IP extraction: source=tcp (no XFF), trusted_proxies=%s", trusted)
        return ip

    parts = [p.strip() for p in xff.split(",") if p.strip()]

    index = len(parts) - trusted
    if 0 <= index < len(parts):
        logger.debug(
            "IP extraction: source=xff, xff_count=%s, trusted_proxies=%s, selected_index=%s",
            len(parts),
            trusted,
            index,
        )
        return parts[index]

    logger.debug(
        "IP extraction: source=xff_fallback, xff_count=%s, trusted_proxies=%s",
        len(parts),
        trusted,
    )
    return parts[0] if parts else (
        request.client.host if request.client else "unknown"
    )


def _raise_if_limited(client_ip: str, bucket: str) -> None:
    if not check_rate_limit(client_ip, bucket=bucket):
        MetadataService.log_rate_limit_block(identifier=f"{bucket}:{hash_identifier(client_ip)}")
        raise AppError(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            "Rate limit exceeded. Try again later.",
            429,
        )


async def verify_rate_limit_extract(request: Request):
    """Scarce quota: transcript extraction (YouTube/Vimeo upstream)."""
    _raise_if_limited(_extract_client_ip(request), "extract")


async def verify_rate_limit_convert(request: Request):
    """Separate bucket so one extract can yield TXT + PDF + DOCX."""
    _raise_if_limited(_extract_client_ip(request), "convert")


async def verify_rate_limit_events(request: Request):
    """High ceiling for product telemetry; does not burn extract quota."""
    _raise_if_limited(_extract_client_ip(request), "events")


async def verify_rate_limit_download(request: Request):
    """Optional light limit; disabled by default (UUID file_id is the gate)."""
    if not settings.rate_limit_download_enabled:
        return
    _raise_if_limited(_extract_client_ip(request), "download")


def check_summarize_quota(request: Request) -> None:
    """Called only on a summary cache miss, so cached summaries never burn quota."""
    _raise_if_limited(_extract_client_ip(request), "summarize")


# Back-compat alias used in older call sites / tests
async def verify_rate_limit(request: Request):
    await verify_rate_limit_extract(request)
