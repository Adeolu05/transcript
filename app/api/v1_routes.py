import asyncio
import os
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import (
    verify_rate_limit_convert,
    verify_rate_limit_download,
    verify_rate_limit_events,
    verify_rate_limit_extract,
)
from app.core.errors import AppError, ErrorCode, success_response
from app.services.analytics_service import AnalyticsService
from app.services.extract_guardrails import enforce_transcript_guardrails
from app.services.file_service import TEMP_DIR, FileGenerator
from app.services.formatter_service import TranscriptFormatter
from app.services.metadata_service import MetadataService
from app.services.telemetry_service import MAX_PAYLOAD_BYTES, TelemetryService
from app.services.transcript_service import get_transcript_from_url
from app.utils.logging_config import logger
from app.utils.validators import detect_platform

router = APIRouter(prefix="/v1")

_ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}
_convert_semaphore = asyncio.Semaphore(settings.convert_max_concurrency)
_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


def _validate_file_id(file_id: str) -> str:
    """Validate file_id is a UUID hex stem with an allowed extension."""
    if ".." in file_id or "/" in file_id or "\\" in file_id:
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    if file_id.endswith(".raw"):
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    stem, _, ext = file_id.rpartition(".")
    if not ext or f".{ext}" not in _ALLOWED_EXTENSIONS:
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    if not stem or not _UUID_HEX_RE.match(stem):
        raise AppError(ErrorCode.FILE_NOT_FOUND, "Invalid file ID.", 400)

    return file_id


class ExtractRequest(BaseModel):
    url: str = Field(..., min_length=20, max_length=2048)
    include_timestamps: bool = False


@router.get("/health")
async def health_check():
    return success_response({"status": "ok", "version": settings.version})


@router.post("/extract", dependencies=[Depends(verify_rate_limit_extract)])
async def extract_transcript(request: ExtractRequest):
    start_time = time.time()

    try:
        platform = detect_platform(request.url)
    except ValueError:
        raise AppError(
            ErrorCode.INVALID_URL,
            "The provided URL is not a supported YouTube or Vimeo link.",
            400,
        )

    layout_format = "timestamp" if request.include_timestamps else "clean"

    try:
        transcript_data = await asyncio.wait_for(
            asyncio.to_thread(get_transcript_from_url, request.url),
            timeout=settings.transcript_timeout_seconds,
        )
    except asyncio.TimeoutError:
        processing_time_ms = int((time.time() - start_time) * 1000)
        MetadataService.log_failure(
            url=request.url,
            platform=platform,
            error_code="UPSTREAM_TIMEOUT",
            error_message="Transcript provider did not respond in time.",
            processing_time_ms=processing_time_ms,
            format_requested=layout_format,
        )
        AnalyticsService.record_event(
            success=False,
            source="web",
            fmt="txt",
            provider=platform,
            processing_time_ms=processing_time_ms,
            error_code="UPSTREAM_TIMEOUT",
        )
        raise AppError(
            ErrorCode.UPSTREAM_TIMEOUT,
            "Transcript provider did not respond in time.",
            504,
        )
    except AppError:
        raise
    except Exception as e:
        err_msg = str(e)
        processing_time_ms = int((time.time() - start_time) * 1000)
        el = err_msg.lower()
        if "disabled" in el:
            code = ErrorCode.TRANSCRIPT_NOT_AVAILABLE
        elif "unavailable" in el or "not found" in el or "no transcript or captions" in el:
            code = ErrorCode.TRANSCRIPT_NOT_AVAILABLE
        elif "youtube blocked" in el or "only available in english" in el:
            code = ErrorCode.TRANSCRIPT_NOT_AVAILABLE
        elif "unsupported" in el:
            code = ErrorCode.INVALID_URL
        else:
            code = ErrorCode.INTERNAL_ERROR
        MetadataService.log_failure(
            url=request.url,
            platform=platform,
            error_code=code.value,
            error_message=err_msg,
            processing_time_ms=processing_time_ms,
            format_requested=layout_format,
        )
        AnalyticsService.record_event(
            success=False,
            source="web",
            fmt="txt",
            provider=platform,
            processing_time_ms=processing_time_ms,
            error_code=code.value,
        )
        status = 400 if code != ErrorCode.INTERNAL_ERROR else 500
        client_msg = (
            "An unexpected error occurred."
            if code == ErrorCode.INTERNAL_ERROR
            else err_msg
        )
        raise AppError(code, client_msg, status)

    # Guardrails (duration estimate, segment/text size) — shared with Telegram
    try:
        duration = enforce_transcript_guardrails(transcript_data)
    except AppError as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        if e.code == ErrorCode.VIDEO_TOO_LONG:
            MetadataService.log_video_too_long(
                video_id=transcript_data.get("video_id", "unknown"),
                provider=platform,
                duration_seconds=int(transcript_data.get("duration_seconds") or 0),
                processing_time_ms=processing_time_ms,
            )
            AnalyticsService.record_event(
                success=False,
                source="web",
                fmt="txt",
                provider=platform,
                duration_seconds=int(transcript_data.get("duration_seconds") or 0),
                processing_time_ms=processing_time_ms,
                error_code="VIDEO_TOO_LONG",
            )
        raise

    formatted_text = await asyncio.to_thread(
        TranscriptFormatter.format, transcript_data["segments"], layout_format
    )

    try:
        enforce_transcript_guardrails(transcript_data, formatted_text=formatted_text)
    except AppError:
        processing_time_ms = int((time.time() - start_time) * 1000)
        AnalyticsService.record_event(
            success=False,
            source="web",
            fmt="txt",
            provider=platform,
            duration_seconds=duration,
            processing_time_ms=processing_time_ms,
            error_code="VIDEO_TOO_LONG",
        )
        raise

    file_path = await asyncio.to_thread(FileGenerator.generate_file, formatted_text, "txt")

    metrics = MetadataService.calculate_metrics(formatted_text)
    processing_time_ms = int((time.time() - start_time) * 1000)
    filename = os.path.basename(file_path)

    text_sidecar = TEMP_DIR / f"{filename}.raw"
    text_sidecar.write_text(formatted_text, encoding="utf-8")

    MetadataService.log_success(
        video_id=transcript_data["video_id"],
        provider=platform,
        duration_seconds=duration,
        processing_time_ms=processing_time_ms,
        word_count=metrics["word_count"],
        format_requested=layout_format,
        file_type="txt",
    )
    AnalyticsService.record_event(
        success=True,
        source="web",
        fmt="txt",
        provider=platform,
        duration_seconds=duration,
        processing_time_ms=processing_time_ms,
    )

    preview_text = formatted_text[:1500]
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=settings.file_ttl_hours)
    ).isoformat()

    return success_response(
        {
            "provider": transcript_data.get("provider", platform),
            "video_id": transcript_data["video_id"],
            "title": transcript_data["title"],
            "language": transcript_data.get("language", "en"),
            "duration_seconds": duration,
            "word_count": metrics["word_count"],
            "reading_time_seconds": metrics["reading_time_seconds"],
            "file_id": filename,
            "file_download_url": f"/api/v1/download/{filename}",
            "preview_text": preview_text,
            "expires_at": expires_at,
        }
    )


@router.get("/download/{file_id}", dependencies=[Depends(verify_rate_limit_download)])
async def download_file(file_id: str):
    _validate_file_id(file_id)

    file_path = TEMP_DIR / file_id

    if not file_path.exists():
        raise AppError(ErrorCode.FILE_EXPIRED, "File not found or expired.", 404)

    extension = file_path.suffix.lower()
    media_type = "text/plain"
    if extension == ".pdf":
        media_type = "application/pdf"
    elif extension == ".docx":
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"transcript{extension}",
        headers={
            "Content-Disposition": f"attachment; filename=transcript{extension}",
            "Cache-Control": "no-store",
        },
    )


class ConvertRequest(BaseModel):
    file_id: str
    format: str  # txt, pdf, docx


@router.post("/convert", dependencies=[Depends(verify_rate_limit_convert)])
async def convert_file(request: ConvertRequest):
    if request.format not in ("txt", "pdf", "docx"):
        raise AppError(
            ErrorCode.CONVERT_FAILED,
            "Unsupported format. Use txt, pdf, or docx.",
            400,
        )

    _validate_file_id(request.file_id)

    if request.format == "txt":
        file_path = TEMP_DIR / request.file_id
        if not file_path.exists():
            raise AppError(ErrorCode.FILE_EXPIRED, "File not found or expired.", 404)
        return success_response(
            {
                "file_download_url": f"/api/v1/download/{request.file_id}",
            }
        )

    sidecar_path = TEMP_DIR / f"{request.file_id}.raw"
    if not sidecar_path.exists():
        raise AppError(ErrorCode.FILE_EXPIRED, "Source text not found or expired.", 404)

    formatted_text = sidecar_path.read_text(encoding="utf-8")

    if len(formatted_text) > settings.max_raw_text_length:
        raise AppError(
            ErrorCode.CONVERT_FAILED,
            "Transcript is too large to convert to this format.",
            400,
        )

    # Non-blocking acquire — no TOCTOU with locked() pre-check
    try:
        await asyncio.wait_for(_convert_semaphore.acquire(), timeout=0.001)
    except asyncio.TimeoutError:
        raise AppError(
            ErrorCode.CONVERT_BUSY,
            "Server busy. Try again shortly.",
            503,
        )

    try:
        try:
            file_path = await asyncio.to_thread(
                FileGenerator.generate_file, formatted_text, request.format
            )
        except Exception as e:
            logger.error("Convert generation failed: %s", e)
            raise AppError(
                ErrorCode.CONVERT_FAILED,
                "Could not generate the requested file format.",
                500,
            )
        filename = os.path.basename(file_path)
    finally:
        _convert_semaphore.release()

    return success_response(
        {
            "file_download_url": f"/api/v1/download/{filename}",
        }
    )


@router.get("/config")
async def get_public_config():
    return success_response(
        {
            "file_ttl_hours": settings.file_ttl_hours,
        }
    )


class EventRequest(BaseModel):
    event_name: str
    session_id: str
    app_source: str
    props: dict | None = None


@router.post("/events", dependencies=[Depends(verify_rate_limit_events)])
async def track_event(request: Request):
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
