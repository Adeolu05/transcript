from fastapi import Request
from app.services.rate_limit_service import check_rate_limit
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.services.metadata_service import MetadataService
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
        # No proxy — use the TCP socket peer directly
        ip = request.client.host if request.client else "unknown"
        logger.debug(f"IP extraction: source=tcp, trusted_proxies=0")
        return ip

    xff = request.headers.get("X-Forwarded-For", "")
    if not xff:
        ip = request.client.host if request.client else "unknown"
        logger.debug(f"IP extraction: source=tcp (no XFF), trusted_proxies={trusted}")
        return ip

    parts = [p.strip() for p in xff.split(",") if p.strip()]

    # The rightmost `trusted` entries were added by our trusted proxies.
    # The entry just before those is the real client IP.
    index = len(parts) - trusted
    if index >= 0 and index < len(parts):
        logger.debug(
            f"IP extraction: source=xff, xff_count={len(parts)}, "
            f"trusted_proxies={trusted}, selected_index={index}"
        )
        return parts[index]

    # Fallback — chain shorter than expected
    logger.debug(
        f"IP extraction: source=xff_fallback, xff_count={len(parts)}, "
        f"trusted_proxies={trusted}"
    )
    return parts[0] if parts else (
        request.client.host if request.client else "unknown"
    )


async def verify_rate_limit(request: Request):
    """
    FastAPI dependency that extracts the real client IP securely
    and checks it against RateLimitService.
    Raises AppError with RATE_LIMIT_EXCEEDED if the limit is exceeded.
    """
    client_ip = _extract_client_ip(request)

    if not check_rate_limit(client_ip):
        MetadataService.log_rate_limit_block(identifier=client_ip)
        raise AppError(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            "Rate limit exceeded. Try again tomorrow.",
            429,
        )
