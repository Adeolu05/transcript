import os
import re
import time
import asyncio
import pathlib
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Conflict
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from dotenv import load_dotenv

from app.utils.validators import detect_platform
from app.services.transcript_service import get_transcript_from_url
from app.services.formatter_service import SUBTITLE_FORMATS, TranscriptFormatter
from app.services.file_service import FileGenerator, download_filename
from app.services.rate_limit_service import check_rate_limit
from app.services.metadata_service import MetadataService
from app.services.extract_guardrails import enforce_transcript_guardrails
from app.core.errors import AppError, ErrorCode, TranscriptFetchError
from app.core.config import settings
from app.utils.logging_config import logger
from app.services.analytics_service import AnalyticsService
from app.services.telemetry_service import TelemetryService, hash_identifier, bucket_duration

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?"
    r"(?:youtube\.com/watch\?[^\s]*v=[^\s]+|youtu\.be/[^\s]+|"
    r"youtube\.com/shorts/[^\s]+|"
    r"(?:www\.)?vimeo\.com/\d+|player\.vimeo\.com/video/\d+)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Per-user preferences (Phase 1 — in-memory)
# ---------------------------------------------------------------------------
_user_prefs: Dict[str, Dict] = {}

# ---------------------------------------------------------------------------
# Avatar path (bundled inside app/ for Docker availability)
# ---------------------------------------------------------------------------
_AVATAR_PATH = pathlib.Path(__file__).parent / "assets" / "telegram-avatar-1024.png"


def _get_prefs(user_id: str) -> dict:
    """Return preferences for *user_id*, creating defaults if absent."""
    if user_id not in _user_prefs:
        _user_prefs[user_id] = {
            "last_file_format": "txt",
            "last_include_timestamps": False,
        }
    return _user_prefs[user_id]


def _set_pref(user_id: str, **kwargs) -> None:
    prefs = _get_prefs(user_id)
    prefs.update(kwargs)


def _emit_event(event_name: str, user_id: str, props: dict | None = None) -> None:
    """Fire-and-forget telemetry for Telegram actions."""
    try:
        TelemetryService.log_event(
            event_name=event_name,
            session_id=hash_identifier(user_id),
            app_source="telegram",
            props=props,
        )
    except Exception:
        pass  # never break bot flow for telemetry


# ---------------------------------------------------------------------------
# Error-code → clean Telegram message mapping
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.INVALID_URL: "Invalid URL.\nOnly YouTube and Vimeo links are supported.",
    ErrorCode.TRANSCRIPT_NOT_AVAILABLE: (
        "No usable captions for this video (or none we could load). Try another link."
    ),
    ErrorCode.VIDEO_TOO_LONG: "Video exceeds maximum supported duration.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded.\nTry again later.",
    ErrorCode.UPSTREAM_TIMEOUT: "Transcript provider did not respond in time.",
    ErrorCode.INTERNAL_ERROR: "Something went wrong.\nTry again.",
}

# ---------------------------------------------------------------------------
# MarkdownV2 helper
# ---------------------------------------------------------------------------

def _escape_md2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


# ---------------------------------------------------------------------------
# Onboarding text constants (pre-escaped MarkdownV2)
# ---------------------------------------------------------------------------

WELCOME_TEXT = (
    "*Transcript Flow*\n\n"
    "Turn YouTube or Vimeo videos into clean transcripts\\.\n\n"
    "\\• YouTube: English captions only at this time\n"
    "\\• TXT \\(default\\)\n"
    "\\• PDF / DOCX\n"
    "\\• SRT / VTT subtitles\n"
    "\\• Optional timestamps\n"
    "\\• No account required\n"
    "\\• Download files expire after about 1 hour\n\n"
    "Send a video link to begin\\.\n"
    "Or try this sample:\n"
    "`/extract https://www\\.youtube\\.com/watch?v\\=dQw4w9WgXcQ`"
)

HELP_TEXT = (
    "*How to use Transcript Flow*\n\n"
    "1\\. Send a YouTube or Vimeo link\\.\n"
    "2\\. Preview the transcript\\.\n"
    "3\\. Download as TXT, PDF, DOCX, SRT, or VTT\\.\n\n"
    "Power users:\n"
    "`/extract <link>`\n\n"
    "If extraction fails:\n"
    "\\• YouTube transcripts are English\\-only for now\\.\n"
    "\\• Captions may be missing or unavailable for some videos\\.\n"
    "\\• Transcripts may be disabled for the video\\."
)

FORMATS_TEXT = (
    "*Available formats*\n\n"
    "TXT  \\– Clean plain text\n"
    "PDF  \\– Printable document\n"
    "DOCX \\– Editable Word file\n"
    "SRT  \\– Subtitles with timings\n"
    "VTT  \\– Web subtitles with timings\n\n"
    "Optional:\n"
    "\\• Include timestamps\n\n"
    "Default format is TXT\\."
)

PRIVACY_TEXT = (
    "*Privacy*\n\n"
    "\\• No account required\\.\n"
    "\\• Generated files auto\\-delete after about 1 hour\\.\n"
    "\\• Short\\-term caption cache \\(hours\\) may reduce repeat fetches\\.\n"
    "\\• We do not keep permanent user accounts or history\\.\n"
    "\\• See the website privacy page for full details\\."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_label(include: bool) -> str:
    return "On" if include else "Off"


def _duration_label(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}m {s}s"


def _reading_time_label(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}m {s}s"


def _format_type_for_prefs(include_timestamps: bool) -> str:
    """Map the boolean timestamp flag to the formatter's format_type arg."""
    return "timestamp" if include_timestamps else "clean"


def _ready_keyboard(include_timestamps: bool) -> InlineKeyboardMarkup:
    """Build the inline keyboard shown on the 'Ready' state."""
    ts_text = f"Timestamps: {_ts_label(include_timestamps)}"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Download TXT", callback_data="dl|txt"),
                InlineKeyboardButton("Download PDF", callback_data="dl|pdf"),
                InlineKeyboardButton("Download DOCX", callback_data="dl|docx"),
            ],
            [
                InlineKeyboardButton("Download SRT", callback_data="dl|srt"),
                InlineKeyboardButton("Download VTT", callback_data="dl|vtt"),
            ],
            [
                InlineKeyboardButton("Preview", callback_data="preview"),
                InlineKeyboardButton(ts_text, callback_data="ts_toggle"),
            ],
            [
                InlineKeyboardButton("New link", callback_data="new_link"),
            ],
        ]
    )


def _ready_text(title: str, duration_s: int, word_count: int, reading_time_s: int) -> str:
    return (
        f"Transcript ready.\n\n"
        f"Title: {title}\n"
        f"Duration: {_duration_label(duration_s)}\n"
        f"Words: {word_count}\n"
        f"Read time: {_reading_time_label(reading_time_s)}"
    )


def _start_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for the /start welcome message."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Try Sample", callback_data="sample"),
            InlineKeyboardButton("Formats", callback_data="formats"),
        ],
        [
            InlineKeyboardButton("Privacy", callback_data="privacy"),
            InlineKeyboardButton("Help", callback_data="help"),
        ],
    ])


async def _build_file(transcript_data: dict, formatted_text: str, ext: str) -> str:
    """Generate *ext* off the event loop (PDF builds can take seconds)."""
    if ext in SUBTITLE_FORMATS:
        content = await asyncio.to_thread(
            TranscriptFormatter.format_subtitles, transcript_data["segments"], ext
        )
    else:
        content = formatted_text
    return await asyncio.to_thread(FileGenerator.generate_file, content, ext)


def _extract_url_from_text(text: str) -> str | None:
    """Return the first YouTube/Vimeo URL found in *text*, or None."""
    match = _URL_PATTERN.search(text)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Core extraction pipeline (reused by /extract, plain-text, and sample button)
# ---------------------------------------------------------------------------

async def _process_url(
    url: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int | None = None,
) -> None:
    """Run the full extraction flow for *url* and post results to the chat."""
    user_id = str(update.effective_user.id)
    target_chat = chat_id or update.effective_chat.id

    # Rate limit (extract bucket — same scarce quota as web extract)
    if not check_rate_limit(f"tg_{user_id}", bucket="extract"):
        _emit_event("tg_rate_limited", user_id)
        await context.bot.send_message(
            chat_id=target_chat,
            text=ERROR_MESSAGES[ErrorCode.RATE_LIMIT_EXCEEDED],
        )
        return

    # Detect platform ----------------------------------------------------
    try:
        platform = detect_platform(url)
    except ValueError:
        await context.bot.send_message(
            chat_id=target_chat,
            text=ERROR_MESSAGES[ErrorCode.INVALID_URL],
        )
        return

    _emit_event("tg_link_received", user_id, {"provider": platform})

    prefs = _get_prefs(user_id)
    file_ext = prefs["last_file_format"]
    include_ts = prefs["last_include_timestamps"]
    fmt_type = _format_type_for_prefs(include_ts)
    started = time.time()

    # State A — Extracting -----------------------------------------------
    status_msg = await context.bot.send_message(
        chat_id=target_chat,
        text=(
            f"Transcript Flow\n\n"
            f"Extracting transcript\u2026\n"
            f"Provider: {platform}\n"
            f"Format: {file_ext}\n"
            f"Timestamps: {_ts_label(include_ts)}"
        ),
    )

    try:
        # Extract (with timeout) -----------------------------------------
        transcript_data = await asyncio.wait_for(
            asyncio.to_thread(get_transcript_from_url, url),
            timeout=settings.transcript_timeout_seconds,
        )

        # Same duration/size policy as HTTP API
        duration = enforce_transcript_guardrails(transcript_data)

        # State B — Formatting -------------------------------------------
        await status_msg.edit_text("Transcript Flow\n\nFormatting transcript\u2026")

        formatted_text = await asyncio.to_thread(
            TranscriptFormatter.format, transcript_data["segments"], fmt_type
        )
        enforce_transcript_guardrails(transcript_data, formatted_text=formatted_text)
        metrics = MetadataService.calculate_metrics(formatted_text)

        # State C — Preparing file ----------------------------------------
        await status_msg.edit_text("Transcript Flow\n\nPreparing file\u2026")

        video_id = transcript_data.get("video_id", "unknown")
        file_path = await _build_file(transcript_data, formatted_text, file_ext)

        # State D — Ready ------------------------------------------------
        ready = _ready_text(
            transcript_data.get("title", "Untitled"),
            duration,
            metrics["word_count"],
            metrics["reading_time_seconds"],
        )
        await status_msg.edit_text(ready, reply_markup=_ready_keyboard(include_ts))

        # Cache everything for callback re-use ----------------------------
        context.user_data["transcript_data"] = transcript_data
        context.user_data["formatted_text"] = formatted_text
        context.user_data["file_path"] = file_path
        context.user_data["file_ext"] = file_ext
        context.user_data["video_id"] = video_id
        context.user_data["status_msg_id"] = status_msg.message_id
        context.user_data["metrics"] = metrics
        context.user_data["url"] = url
        context.user_data["platform"] = platform
        context.user_data["_processing"] = False

        processing_time_ms = int((time.time() - started) * 1000)
        _emit_event("tg_extract_succeeded", user_id, {
            "provider": platform,
            "duration_seconds_bucket": bucket_duration(duration),
            "file_format": file_ext,
        })
        AnalyticsService.record_event(
            success=True, source="telegram", fmt=file_ext, provider=platform,
            duration_seconds=duration,
            processing_time_ms=processing_time_ms,
        )

    except asyncio.TimeoutError:
        _emit_event("tg_extract_failed", user_id, {"error_code": "UPSTREAM_TIMEOUT", "provider": platform})
        AnalyticsService.record_event(
            success=False, source="telegram", fmt=file_ext, provider=platform,
            error_code="UPSTREAM_TIMEOUT",
            processing_time_ms=int((time.time() - started) * 1000),
        )
        await status_msg.edit_text(ERROR_MESSAGES[ErrorCode.UPSTREAM_TIMEOUT])
    except AppError as e:
        msg = ERROR_MESSAGES.get(e.code, e.message)
        _emit_event("tg_extract_failed", user_id, {"error_code": e.code.value, "provider": platform})
        AnalyticsService.record_event(
            success=False, source="telegram", fmt=file_ext, provider=platform,
            error_code=e.code.value,
            processing_time_ms=int((time.time() - started) * 1000),
        )
        await status_msg.edit_text(msg)
    except Exception as e:
        if isinstance(e, TranscriptFetchError):
            # Service messages are written for end users (e.g. "disabled", "blocked")
            friendly = e.message
            error_code = e.code.value
        else:
            logger.exception("Error processing URL")
            friendly = ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR]
            error_code = "INTERNAL_ERROR"

        _emit_event("tg_extract_failed", user_id, {"error_code": error_code, "provider": platform})
        AnalyticsService.record_event(
            success=False, source="telegram", fmt=file_ext, provider=platform,
            error_code=error_code,
            processing_time_ms=int((time.time() - started) * 1000),
        )
        await status_msg.edit_text(friendly)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    _emit_event("tg_cmd_start", user_id)

    if _AVATAR_PATH.exists():
        with open(_AVATAR_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=WELCOME_TEXT,
                parse_mode="MarkdownV2",
                reply_markup=_start_keyboard(),
            )
    else:
        await update.message.reply_text(
            WELCOME_TEXT,
            parse_mode="MarkdownV2",
            reply_markup=_start_keyboard(),
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _emit_event("tg_cmd_help", str(update.effective_user.id))
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


async def extract_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    _emit_event("tg_cmd_extract", user_id)

    # Parse argument(s) after /extract
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /extract <link>\n\n"
            "Example:\n/extract https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        return

    url = " ".join(args).strip()

    # Validate URL
    try:
        detect_platform(url)
    except ValueError:
        await update.message.reply_text(
            "Invalid link. Only YouTube and Vimeo URLs are supported.\n\n"
            "Example:\n/extract https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        return

    await _process_url(url, update, context)


async def formats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _emit_event("tg_cmd_formats", str(update.effective_user.id))
    await update.message.reply_text(FORMATS_TEXT, parse_mode="MarkdownV2")


async def privacy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _emit_event("tg_cmd_privacy", str(update.effective_user.id))
    await update.message.reply_text(PRIVACY_TEXT, parse_mode="MarkdownV2")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _emit_event("tg_cmd_status", str(update.effective_user.id))

    # Quick health check — verify core services are importable
    api_status = "Online"
    try:
        # Attempt a lightweight import check of critical services
        from app.services.transcript_service import get_transcript_from_url as _check  # noqa: F401
        from app.services.file_service import FileGenerator as _check2  # noqa: F401
    except Exception:
        api_status = "Degraded"

    await update.message.reply_text(
        "Service Status\n\n"
        f"API: {api_status}\n"
        "Rate limit: Active\n"
        "File expiry: 1 hour"
    )


# ---------------------------------------------------------------------------
# Plain-text message handler (raw links or hint)
# ---------------------------------------------------------------------------

async def handle_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    url = _extract_url_from_text(text)

    if url:
        await _process_url(url, update, context)
    else:
        await update.message.reply_text("Send a YouTube/Vimeo link or use /help")


# ---------------------------------------------------------------------------
# Callback query router
# ---------------------------------------------------------------------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    # Onboarding inline-button callbacks ----------------------------------
    if data == "sample":
        await query.answer("Extracting sample\u2026")
        _emit_event("tg_sample_clicked", str(query.from_user.id))
        await _process_url(SAMPLE_URL, update, context, chat_id=query.message.chat_id)

    elif data == "help":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=HELP_TEXT,
            parse_mode="MarkdownV2",
        )

    elif data == "formats":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=FORMATS_TEXT,
            parse_mode="MarkdownV2",
        )

    elif data == "privacy":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=PRIVACY_TEXT,
            parse_mode="MarkdownV2",
        )

    # Legacy onboarding callbacks (backward compat) -----------------------
    elif data == "onboard_help":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=HELP_TEXT,
            parse_mode="MarkdownV2",
        )
    elif data == "onboard_privacy":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=PRIVACY_TEXT,
            parse_mode="MarkdownV2",
        )

    # Extraction callbacks ------------------------------------------------
    elif data.startswith("dl|"):
        await _handle_download(query, context, data.split("|")[1])
    elif data == "preview":
        await _handle_preview(query, context)
    elif data == "ts_toggle":
        await _handle_timestamp_toggle(query, context)
    elif data == "new_link":
        await _handle_new_link(query, context)
    elif data.startswith("preview_dl|"):
        await _handle_preview_download(query, context, data.split("|")[1])
    elif data == "preview_back":
        await _handle_preview_back(query, context)
    else:
        await query.answer()


# ---------------------------------------------------------------------------
# Download callback
# ---------------------------------------------------------------------------

async def _handle_download(query, context: ContextTypes.DEFAULT_TYPE, ext: str) -> None:
    # Anti-spam: guard against concurrent processing ----------------------
    if context.user_data.get("_processing"):
        await query.answer("Processing\u2026")
        return
    context.user_data["_processing"] = True
    await query.answer("Processing\u2026")

    try:
        formatted_text = context.user_data.get("formatted_text")
        transcript_data = context.user_data.get("transcript_data") or {}
        user_id = str(query.from_user.id)

        _emit_event("tg_download_clicked", user_id, {"file_format": ext})

        if not formatted_text or not transcript_data:
            await query.answer("Session expired. Send the link again.")
            context.user_data["_processing"] = False
            return

        # Re-use cached file if extension matches and TTL cleanup hasn't removed it
        cached_path = context.user_data.get("file_path")
        if ext == context.user_data.get("file_ext") and cached_path and os.path.exists(cached_path):
            file_path = cached_path
        else:
            file_path = await _build_file(transcript_data, formatted_text, ext)

        # Send file -------------------------------------------------------
        with open(file_path, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=download_filename(transcript_data.get("title"), ext),
            )

        # Update preference ------------------------------------------------
        _set_pref(user_id, last_file_format=ext)

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.answer("Something went wrong.")
    finally:
        context.user_data["_processing"] = False


# ---------------------------------------------------------------------------
# Preview callback
# ---------------------------------------------------------------------------

async def _handle_preview(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    await query.answer()

    formatted_text = context.user_data.get("formatted_text")
    if not formatted_text:
        await query.answer("Session expired. Send the link again.")
        return

    _emit_event("tg_preview_clicked", str(query.from_user.id))

    limit = settings.preview_chars
    truncated = len(formatted_text) > limit
    preview = formatted_text[:limit]

    text = f"Preview (truncated)\n\n{preview}"
    if truncated:
        text += "\n\nShowing shortened preview. Download file for full transcript."

    user_id = str(query.from_user.id)
    prefs = _get_prefs(user_id)
    current_fmt = prefs["last_file_format"]

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Download {current_fmt.upper()}", callback_data=f"preview_dl|{current_fmt}")],
            [InlineKeyboardButton("Back", callback_data="preview_back")],
        ]
    )

    preview_msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=keyboard,
    )
    context.user_data["preview_msg_id"] = preview_msg.message_id


# ---------------------------------------------------------------------------
# Preview-specific download
# ---------------------------------------------------------------------------

async def _handle_preview_download(query, context: ContextTypes.DEFAULT_TYPE, ext: str) -> None:
    await _handle_download(query, context, ext)


# ---------------------------------------------------------------------------
# Preview back — delete preview message
# ---------------------------------------------------------------------------

async def _handle_preview_back(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    await query.answer()
    try:
        preview_id = context.user_data.get("preview_msg_id")
        if preview_id:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=preview_id,
            )
            context.user_data.pop("preview_msg_id", None)
    except Exception as e:
        logger.error(f"Could not delete preview message: {e}")


# ---------------------------------------------------------------------------
# Timestamp toggle callback
# ---------------------------------------------------------------------------

async def _handle_timestamp_toggle(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    await query.answer()

    user_id = str(query.from_user.id)
    prefs = _get_prefs(user_id)
    new_ts = not prefs["last_include_timestamps"]
    _set_pref(user_id, last_include_timestamps=new_ts)

    transcript_data = context.user_data.get("transcript_data")
    if not transcript_data:
        await query.answer("Session expired. Send the link again.")
        return

    # Re-format with new timestamp state ----------------------------------
    fmt_type = _format_type_for_prefs(new_ts)
    formatted_text = await asyncio.to_thread(
        TranscriptFormatter.format, transcript_data["segments"], fmt_type
    )
    metrics = MetadataService.calculate_metrics(formatted_text)

    # Regenerate file in current preferred format -------------------------
    file_ext = prefs["last_file_format"]
    file_path = await _build_file(transcript_data, formatted_text, file_ext)

    # Update cache --------------------------------------------------------
    context.user_data["formatted_text"] = formatted_text
    context.user_data["file_path"] = file_path
    context.user_data["file_ext"] = file_ext
    context.user_data["metrics"] = metrics

    # Edit the main status message ----------------------------------------
    ready = _ready_text(
        transcript_data.get("title", "Untitled"),
        transcript_data.get("duration_seconds", 0),
        metrics["word_count"],
        metrics["reading_time_seconds"],
    )
    try:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=context.user_data.get("status_msg_id", query.message.message_id),
            text=ready,
            reply_markup=_ready_keyboard(new_ts),
        )
    except Exception as e:
        logger.error(f"Could not edit status message on ts toggle: {e}")


# ---------------------------------------------------------------------------
# New link callback
# ---------------------------------------------------------------------------

async def _handle_new_link(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    await query.answer()

    # Clear extraction cache but keep user preferences --------------------
    for key in ("transcript_data", "formatted_text", "file_path",
                "file_ext", "video_id", "status_msg_id", "metrics",
                "url", "platform", "preview_msg_id"):
        context.user_data.pop(key, None)

    await query.edit_message_text("Transcript Flow\n\nSend a YouTube or Vimeo link.")


# ---------------------------------------------------------------------------
# Global error handler (avoids silent "No error handlers" spam)
# ---------------------------------------------------------------------------

async def _telegram_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, Conflict):
        logger.error(
            "Telegram Conflict: only one process may poll this bot. "
            "Stop every other instance using the same TELEGRAM_BOT_TOKEN "
            "(other terminals, Cursor background jobs, Render worker, etc.), "
            "then start the bot again. If you used webhooks before, run /deleteWebhook in @BotFather or call deleteWebhook."
        )
        return
    logger.exception("Unhandled error in Telegram handler", exc_info=err)


# ---------------------------------------------------------------------------
# Bot entry point
# ---------------------------------------------------------------------------

def run_bot() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    application = ApplicationBuilder().token(token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("extract", extract_cmd))
    application.add_handler(CommandHandler("formats", formats_cmd))
    application.add_handler(CommandHandler("privacy", privacy_cmd))
    application.add_handler(CommandHandler("status", status_cmd))

    # Plain-text message handler (catches raw links)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_plain_text))

    # Inline button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    application.add_error_handler(_telegram_error_handler)

    print("Bot is polling...")
    application.run_polling()


if __name__ == "__main__":
    run_bot()
