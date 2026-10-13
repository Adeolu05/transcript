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
from app.core.errors import AppError, ErrorCode, TranscriptFetchError, success_response
from app.core.languages import (
    DEFAULT_LANGUAGE,
    LANGUAGE_CODES,
    language_name,
    languages_match,
    public_language_list,
)
from app.services.analytics_service import AnalyticsService
from app.services.extract_guardrails import enforce_transcript_guardrails
from app.services.file_service import (
    TEMP_DIR,
    FileGenerator,
    content_disposition,
    download_filename,
    read_sidecar,
    write_sidecar,
)
from app.services.formatter_service import SUBTITLE_FORMATS, TranscriptFormatter
from app.services.pdf_fonts import UnsupportedPdfScript, pdf_supported
from app.services.metadata_service import MetadataService
from app.services.telemetry_service import MAX_PAYLOAD_BYTES, TelemetryService
from app.services.transcript_service import get_transcript_from_url
from app.utils.logging_config import logger
from app.utils.validators import detect_platform

router = APIRouter(prefix="/v1")

_CONVERT_FORMATS = ("txt", "pdf", "docx", *SUBTITLE_FORMATS)
_ALLOWED_EXTENSIONS = {f".{fmt}" for fmt in _CONVERT_FORMATS}
_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".srt": "application/x-subrip",
    ".vtt": "text/vtt",
}
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
    # Target caption language (see app.core.languages); YouTube auto-translates
    language: str = DEFAULT_LANGUAGE


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

    if request.language not in LANGUAGE_CODES:
        raise AppError(ErrorCode.UNSUPPORTED_LANGUAGE, "That language isn't supported.", 400)

    layout_format = "timestamp" if request.include_timestamps else "clean"

    # The worker thread outlives wait_for; the deadline makes it stop calling upstream too
    deadline = time.monotonic() + settings.transcript_timeout_seconds
    try:
        transcript_data = await asyncio.wait_for(
            asyncio.to_thread(
                get_transcript_from_url, request.url, deadline, request.language
            ),
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
        if isinstance(e, TranscriptFetchError):
            code, status = e.code, e.status_code
        else:
            code, status = ErrorCode.INTERNAL_ERROR, 500
            logger.exception("Unexpected transcript fetch failure")
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
    # Segments feed SRT/VTT convert; title names every download of this transcript
    await asyncio.to_thread(write_sidecar, filename, "segments", transcript_data["segments"])
    out_language = transcript_data.get("language", DEFAULT_LANGUAGE)
    # Language picks the CJK PDF font (zh-Hant vs zh-Hans) at convert time
    write_sidecar(filename, "meta", {"title": transcript_data.get("title"), "language": out_language})
    can_pdf = await asyncio.to_thread(pdf_supported, formatted_text)
    source_language = transcript_data.get("source_language") or out_language
    translated = bool(transcript_data.get("translated"))

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

    preview_text = formatted_text[: settings.preview_chars]
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=settings.file_ttl_hours)
    ).isoformat()

    return success_response(
        {
            "provider": transcript_data.get("provider", platform),
            "video_id": transcript_data["video_id"],
            "title": transcript_data["title"],
            "language": out_language,
            "language_name": language_name(out_language),
            "requested_language": request.language,
            "source_language": source_language,
            "source_language_name": language_name(source_language),
            "translated": translated,
            # Neither a native track nor a translation: captions are in another language
            "language_fallback": not translated
            and not languages_match(out_language, request.language),
            "pdf_supported": can_pdf,
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
    meta = read_sidecar(file_id, "meta") or {}
    filename = download_filename(meta.get("title"), extension)

    return FileResponse(
        path=str(file_path),
        media_type=_MEDIA_TYPES.get(extension, "text/plain"),
        headers={
            "Content-Disposition": content_disposition(filename),
            "Cache-Control": "no-store",
        },
    )


class ConvertRequest(BaseModel):
    file_id: str
    format: str  # txt, pdf, docx, srt, vtt


@router.post("/convert", dependencies=[Depends(verify_rate_limit_convert)])
async def convert_file(request: ConvertRequest):
    if request.format not in _CONVERT_FORMATS:
        raise AppError(
            ErrorCode.CONVERT_FAILED,
            "Unsupported format. Use txt, pdf, docx, srt, or vtt.",
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

    if request.format in SUBTITLE_FORMATS:
        segments = await asyncio.to_thread(read_sidecar, request.file_id, "segments")
        if not isinstance(segments, list):
            raise AppError(ErrorCode.FILE_EXPIRED, "Source captions not found or expired.", 404)
        # Segment count/size were already capped by the extract guardrails
        content = await asyncio.to_thread(
            TranscriptFormatter.format_subtitles, segments, request.format
        )
    else:
        sidecar_path = TEMP_DIR / f"{request.file_id}.raw"
        if not sidecar_path.exists():
            raise AppError(ErrorCode.FILE_EXPIRED, "Source text not found or expired.", 404)
        content = sidecar_path.read_text(encoding="utf-8")

        if len(content) > settings.max_raw_text_length:
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
                FileGenerator.generate_file,
                content,
                request.format,
                (read_sidecar(request.file_id, "meta") or {}).get("language", ""),
            )
        except UnsupportedPdfScript as e:
            raise AppError(ErrorCode.CONVERT_FAILED, str(e), 400)
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

    meta = read_sidecar(request.file_id, "meta")
    if meta:
        write_sidecar(filename, "meta", meta)

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
            "default_language": DEFAULT_LANGUAGE,
            "languages": public_language_list(),
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
