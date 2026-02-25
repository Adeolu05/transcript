import re
import time
import os
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.transcript_service import get_transcript_from_url
from app.services.formatter_service import TranscriptFormatter
from app.services.file_service import FileGenerator, TEMP_DIR
from app.services.metadata_service import MetadataService
from app.services.analytics_service import AnalyticsService
from app.utils.validators import detect_platform
from app.core.dependencies import verify_rate_limit
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, success_response
from app.utils.logging_config import logger
from app.services.telemetry_service import TelemetryService, MAX_PAYLOAD_BYTES

router = APIRouter(prefix="/v1")

# ── Allowed extensions & UUID pattern for file_id validation ─────────
_ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx'}

# Concurrency limiter for CPU-heavy PDF/DOCX generation
_convert_semaphore = asyncio.Semaphore(settings.convert_max_concurrency)
_UUID_HEX_RE = re.compile(r'^[0-9a-f]{32}$')


def _validate_file_id(file_id: str) -> str:
    """Validate file_id is a UUID hex stem with an allowed extension.
    Returns the validated file_id or raises AppError."""
    # Block path traversal
    if '..' in file_id or '/' in file_id or '\\' in file_id:
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    # Block raw sidecar access
    if file_id.endswith('.raw'):
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    # Must have an allowed extension
    stem, _, ext = file_id.rpartition('.')
    if not ext or f'.{ext}' not in _ALLOWED_EXTENSIONS:
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    # Stem must be a valid 32-char hex UUID
    if not stem or not _UUID_HEX_RE.match(stem):
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    return file_id


class ExtractRequest(BaseModel):
    url: str
    include_timestamps: bool = False


# ── Health ────────────────────────────────────────────────────────────
@router.get("/health")
async def health_check():
    return success_response({"status": "ok", "version": settings.version})


# ── Extract ───────────────────────────────────────────────────────────
@router.post("/extract", dependencies=[Depends(verify_rate_limit)])
async def extract_transcript(request: ExtractRequest, background_tasks: BackgroundTasks):
    start_time = time.time()

    # Validate platform
    try:
        platform = detect_platform(request.url)
    except ValueError:
        raise AppError(ErrorCode.INVALID_URL, "The provided URL is not a supported YouTube or Vimeo link.", 400)

    # 1. Fetch transcript with timeout protection
    try:
        transcript_data = await asyncio.wait_for(
            asyncio.to_thread(get_transcript_from_url, request.url),
            timeout=settings.transcript_timeout_seconds,
        )
    except asyncio.TimeoutError:
        processing_time_ms = int((time.time() - start_time) * 1000)
        MetadataService.log_failure(
            url=request.url, platform=platform, error_code="UPSTREAM_TIMEOUT",
            error_message="Transcript provider did not respond in time.",
            processing_time_ms=processing_time_ms, format_requested=request.format,
        )
        AnalyticsService.record_event(
            success=False, source="web", fmt=request.format, provider=platform,
            processing_time_ms=processing_time_ms, error_code="UPSTREAM_TIMEOUT",
        )
        raise AppError(ErrorCode.UPSTREAM_TIMEOUT, "Transcript provider did not respond in time.", 504)
    except Exception as e:
        err_msg = str(e)
        processing_time_ms = int((time.time() - start_time) * 1000)
        # Map known error messages to stable codes
        if "disabled" in err_msg.lower():
            code = ErrorCode.TRANSCRIPT_NOT_AVAILABLE
        elif "unavailable" in err_msg.lower() or "not found" in err_msg.lower():
            code = ErrorCode.TRANSCRIPT_NOT_AVAILABLE
        elif "unsupported" in err_msg.lower():
            code = ErrorCode.INVALID_URL
        else:
            code = ErrorCode.INTERNAL_ERROR
        MetadataService.log_failure(
            url=request.url, platform=platform, error_code=code.value,
            error_message=err_msg, processing_time_ms=processing_time_ms,
            format_requested=request.format,
        )
        AnalyticsService.record_event(
            success=False, source="web", fmt=request.format, provider=platform,
            processing_time_ms=processing_time_ms, error_code=code.value,
        )
        status = 400 if code != ErrorCode.INTERNAL_ERROR else 500
        raise AppError(code, err_msg, status)

    # 2. Duration guardrail
    duration = transcript_data.get('duration_seconds', 0)
    if duration > settings.max_video_duration_seconds:
        processing_time_ms = int((time.time() - start_time) * 1000)
        MetadataService.log_video_too_long(
            video_id=transcript_data['video_id'], provider=platform,
            duration_seconds=duration, processing_time_ms=processing_time_ms,
        )
        AnalyticsService.record_event(
            success=False, source="web", fmt=request.format, provider=platform,
            duration_seconds=duration, processing_time_ms=processing_time_ms,
            error_code="VIDEO_TOO_LONG",
        )
        raise AppError(
            ErrorCode.VIDEO_TOO_LONG,
            "Video exceeds maximum supported duration.",
            400,
        )

    # 3. Format
    format_type = 'timestamp' if request.include_timestamps else 'clean'
    formatted_text = await asyncio.to_thread(
        TranscriptFormatter.format, transcript_data['segments'], format_type
    )

    # 4. Generate TXT file (base format for preview + convert)
    file_path = await asyncio.to_thread(
        FileGenerator.generate_file, formatted_text, 'txt'
    )

    # 5. Calculate metadata
    metrics = MetadataService.calculate_metrics(formatted_text)
    processing_time_ms = int((time.time() - start_time) * 1000)
    filename = os.path.basename(file_path)

    # 6. Store raw text alongside the file for convert endpoint
    text_sidecar = TEMP_DIR / f"{filename}.raw"
    text_sidecar.write_text(formatted_text, encoding='utf-8')

    # 7. Log success
    MetadataService.log_success(
        video_id=transcript_data['video_id'],
        provider=platform,
        duration_seconds=duration,
        processing_time_ms=processing_time_ms,
        word_count=metrics['word_count'],
        format_requested=format_type,
        file_type='txt',
    )
    AnalyticsService.record_event(
        success=True, source="web", fmt='txt', provider=platform,
        duration_seconds=duration, processing_time_ms=processing_time_ms,
    )

    # 8. Preview text (first 1500 chars)
    preview_text = formatted_text[:1500]

    # 9. Compute expiry timestamp
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=settings.file_ttl_hours)).isoformat()

    # 10. Return full envelope with preview
    return success_response({
        "provider": transcript_data.get('provider', platform),
        "video_id": transcript_data['video_id'],
        "title": transcript_data['title'],
        "language": transcript_data.get('language', 'en'),
        "duration_seconds": duration,
        "word_count": metrics['word_count'],
        "reading_time_seconds": metrics['reading_time_seconds'],
        "file_id": filename,
        "file_download_url": f"/api/v1/download/{filename}",
        "preview_text": preview_text,
        "expires_at": expires_at,
    })


# ── Download ──────────────────────────────────────────────────────────
@router.get("/download/{file_id}")
async def download_file(file_id: str):
    # Strict validation: UUID stem + allowed extension, blocks traversal & .raw
    _validate_file_id(file_id)

    file_path = TEMP_DIR / file_id

    if not file_path.exists():
        raise AppError(ErrorCode.FILE_EXPIRED, "File not found or expired.", 404)

    extension = file_path.suffix.lower()
    media_type = "text/plain"
    if extension == '.pdf':
        media_type = "application/pdf"
    elif extension == '.docx':
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"transcript{extension}",
        headers={
            "Content-Disposition": f"attachment; filename=transcript{extension}",
            "Cache-Control": "no-store",
        },
    )


# ── Convert ──────────────────────────────────────────────────────────
class ConvertRequest(BaseModel):
    file_id: str
    format: str  # txt, pdf, docx


@router.post("/convert", dependencies=[Depends(verify_rate_limit)])
async def convert_file(request: ConvertRequest):
    if request.format not in ('txt', 'pdf', 'docx'):
        raise AppError(ErrorCode.CONVERT_FAILED, "Unsupported format. Use txt, pdf, or docx.", 400)

    # Strict validation: UUID stem + allowed extension, blocks traversal & .raw
    _validate_file_id(request.file_id)

    # If TXT, return the original file
    if request.format == 'txt':
        file_path = TEMP_DIR / request.file_id
        if not file_path.exists():
            raise AppError(ErrorCode.FILE_EXPIRED, "File not found or expired.", 404)
        return success_response({
            "file_download_url": f"/api/v1/download/{request.file_id}",
        })

    # Read the raw text sidecar (never calls external providers)
    sidecar_path = TEMP_DIR / f"{request.file_id}.raw"
    if not sidecar_path.exists():
        raise AppError(ErrorCode.FILE_EXPIRED, "Source text not found or expired.", 404)

    formatted_text = sidecar_path.read_text(encoding='utf-8')

    # Size guard — refuse conversion if text is too large
    if len(formatted_text) > settings.max_raw_text_length:
        raise AppError(
            ErrorCode.CONVERT_FAILED,
            "Transcript is too large to convert to this format.",
            400,
        )

    # Acquire concurrency slot (non-blocking — reject if all slots busy)
    if _convert_semaphore.locked():
        raise AppError(
            ErrorCode.CONVERT_BUSY,
            "Server busy. Try again shortly.",
            503,
        )

    async with _convert_semaphore:
        # Generate the requested format
        try:
            file_path = await asyncio.to_thread(
                FileGenerator.generate_file, formatted_text, request.format
            )
        except Exception as e:
            logger.error(f"Convert generation failed: {e}")
            raise AppError(
                ErrorCode.CONVERT_FAILED,
                "Could not generate the requested file format.",
                500,
            )
        filename = os.path.basename(file_path)

    return success_response({
        "file_download_url": f"/api/v1/download/{filename}",
    })


# ── Config (public, read-only) ───────────────────────────────────────
@router.get("/config")
async def get_public_config():
    return success_response({
        "file_ttl_hours": settings.file_ttl_hours,
    })


# ── Telemetry events ─────────────────────────────────────────────────
class EventRequest(BaseModel):
    event_name: str
    session_id: str
    app_source: str
    props: dict | None = None


@router.post("/events", dependencies=[Depends(verify_rate_limit)])
async def track_event(request: Request):
    # Payload size guard
    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise AppError(ErrorCode.CONVERT_FAILED, "Payload too large.", 400)

    data = EventRequest.model_validate_json(body)

    accepted = TelemetryService.log_event(
        event_name=data.event_name,
        session_id=data.session_id,
        app_source=data.app_source,
        props=data.props,
    )

    if not accepted:
        raise AppError(ErrorCode.CONVERT_FAILED, "Invalid event.", 400)

    return success_response({"accepted": True})
