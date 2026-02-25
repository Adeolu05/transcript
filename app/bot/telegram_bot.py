import os
import asyncio
import pathlib
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
from app.services.formatter_service import TranscriptFormatter
from app.services.file_service import FileGenerator
from app.services.rate_limit_service import check_rate_limit
from app.services.metadata_service import MetadataService
from app.core.errors import AppError, ErrorCode
from app.core.config import settings
from app.utils.logging_config import logger
from app.services.analytics_service import AnalyticsService
from app.services.telemetry_service import TelemetryService, hash_identifier, bucket_duration

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

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
# Error-code → clean Telegram message mapping (no emojis)
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.INVALID_URL: "Invalid URL.\nOnly YouTube and Vimeo links are supported.",
    ErrorCode.TRANSCRIPT_NOT_AVAILABLE: "Transcript not available for this video.",
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

HELP_TEXT = (
    "*How to use Transcript Flow*\n\n"
    "1\\. Send a YouTube or Vimeo link\\.\n"
    "2\\. The bot extracts the transcript automatically\\.\n"
    "3\\. Download as TXT, PDF, or DOCX\\.\n\n"
    "Use the Timestamps button to toggle timestamps "
    "on or off\\. Your preference is remembered\\."
)

PRIVACY_TEXT = (
    "*Privacy*\n\n"
    "\\• No account required\\.\n"
    "\\• Generated files are auto\\-deleted after 1 hour\\.\n"
    "\\• No persistent storage of transcripts or user data\\."
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


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    _emit_event("tg_start", user_id)

    caption = (
        "*Transcript Flow*\n\n"
        "Extract transcripts from YouTube and Vimeo links\\.\n\n"
        "Send a video link and receive a clean text file "
        "in seconds\\.\n\n"
        "\\• TXT \\(default\\)\n"
        "\\• PDF\n"
        "\\• DOCX\n"
        "\\• Optional timestamps\n"
        "\\• No account required\n\n"
        "_Files expire after 1 hour\\._\n\n"
        "Send a link to begin\\."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Open Web App", url="https://usetranscriptflow.com")],
        [
            InlineKeyboardButton("Help", callback_data="onboard_help"),
            InlineKeyboardButton("Privacy", callback_data="onboard_privacy"),
        ],
    ])

    with open(_AVATAR_PATH, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=caption,
            parse_mode="MarkdownV2",
            reply_markup=keyboard,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _emit_event("tg_help", str(update.effective_user.id))
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


# ---------------------------------------------------------------------------
# URL handler — instant processing via single edited message
# ---------------------------------------------------------------------------

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # Rate limit ---------------------------------------------------------
    if not check_rate_limit(f"tg_{user_id}"):
        _emit_event("tg_rate_limited", user_id)
        await update.message.reply_text(ERROR_MESSAGES[ErrorCode.RATE_LIMIT_EXCEEDED])
        return

    # Detect platform ----------------------------------------------------
    try:
        platform = detect_platform(url)
    except ValueError:
        await update.message.reply_text(ERROR_MESSAGES[ErrorCode.INVALID_URL])
        return

    _emit_event("tg_link_received", user_id, {"provider": platform})

    prefs = _get_prefs(user_id)
    file_ext = prefs["last_file_format"]
    include_ts = prefs["last_include_timestamps"]
    fmt_type = _format_type_for_prefs(include_ts)

    # State A — Extracting -----------------------------------------------
    status_msg = await update.message.reply_text(
        f"Transcript Flow\n\n"
        f"Extracting transcript\u2026\n"
        f"Provider: {platform}\n"
        f"Format: {file_ext}\n"
        f"Timestamps: {_ts_label(include_ts)}"
    )

    try:
        # Extract (with timeout) -----------------------------------------
        transcript_data = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, get_transcript_from_url, url),
            timeout=settings.transcript_timeout_seconds,
        )

        # State B — Formatting -------------------------------------------
        await status_msg.edit_text("Transcript Flow\n\nFormatting transcript\u2026")

        formatted_text = TranscriptFormatter.format(
            transcript_data["segments"], format_type=fmt_type
        )
        metrics = MetadataService.calculate_metrics(formatted_text)

        # State C — Preparing file ----------------------------------------
        await status_msg.edit_text("Transcript Flow\n\nPreparing file\u2026")

        video_id = transcript_data.get("video_id", "unknown")
        file_path = FileGenerator.generate_file(formatted_text, file_ext)

        # State D — Ready ------------------------------------------------
        ready = _ready_text(
            title=transcript_data.get("title", "Untitled"),
            duration_s=transcript_data.get("duration_seconds", 0),
            word_count=metrics["word_count"],
            reading_time_s=metrics["reading_time_seconds"],
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

        # Log success event
        _emit_event("tg_extract_succeeded", user_id, {
            "provider": platform,
            "duration_seconds_bucket": bucket_duration(transcript_data.get("duration_seconds", 0)),
            "file_format": file_ext,
        })
        AnalyticsService.record_event(
            success=True, source="telegram", fmt=file_ext, provider=platform,
            duration_seconds=transcript_data.get("duration_seconds", 0),
            processing_time_ms=int((asyncio.get_event_loop().time()) * 1000),
        )

    except asyncio.TimeoutError:
        _emit_event("tg_extract_failed", user_id, {"error_code": "UPSTREAM_TIMEOUT", "provider": platform})
        AnalyticsService.record_event(
            success=False, source="telegram", fmt=file_ext, provider=platform,
            error_code="UPSTREAM_TIMEOUT",
        )
        await status_msg.edit_text(ERROR_MESSAGES[ErrorCode.UPSTREAM_TIMEOUT])
    except AppError as e:
        msg = ERROR_MESSAGES.get(e.code, f"{e.message}")
        await status_msg.edit_text(msg)
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        _emit_event("tg_extract_failed", user_id, {"error_code": "INTERNAL_ERROR", "provider": platform})
        AnalyticsService.record_event(
            success=False, source="telegram", fmt=file_ext, provider=platform,
            error_code="INTERNAL_ERROR",
        )
        await status_msg.edit_text(ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR])


# ---------------------------------------------------------------------------
# Callback query router
# ---------------------------------------------------------------------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # Onboarding callbacks ------------------------------------------------
    if data == "onboard_help":
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

async def _handle_download(query, context: ContextTypes.DEFAULT_TYPE, ext: str):
    # Anti-spam: guard against concurrent processing ----------------------
    if context.user_data.get("_processing"):
        await query.answer("Processing\u2026")
        return
    context.user_data["_processing"] = True
    await query.answer("Processing\u2026")

    try:
        formatted_text = context.user_data.get("formatted_text")
        video_id = context.user_data.get("video_id", "unknown")
        user_id = str(query.from_user.id)

        _emit_event("tg_download_clicked", user_id, {"file_format": ext})

        if not formatted_text:
            await query.answer("Session expired. Send the link again.")
            context.user_data["_processing"] = False
            return

        # Re-use cached file if extension matches, otherwise regenerate ---
        cached_ext = context.user_data.get("file_ext")
        if ext == cached_ext and context.user_data.get("file_path"):
            file_path = context.user_data["file_path"]
        else:
            file_path = FileGenerator.generate_file(formatted_text, ext)

        # Send file -------------------------------------------------------
        with open(file_path, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"transcriptflow_{video_id}.{ext}",
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

async def _handle_preview(query, context: ContextTypes.DEFAULT_TYPE):
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

async def _handle_preview_download(query, context: ContextTypes.DEFAULT_TYPE, ext: str):
    await _handle_download(query, context, ext)


# ---------------------------------------------------------------------------
# Preview back — delete preview message
# ---------------------------------------------------------------------------

async def _handle_preview_back(query, context: ContextTypes.DEFAULT_TYPE):
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

async def _handle_timestamp_toggle(query, context: ContextTypes.DEFAULT_TYPE):
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
    formatted_text = TranscriptFormatter.format(
        transcript_data["segments"], format_type=fmt_type
    )
    metrics = MetadataService.calculate_metrics(formatted_text)

    # Regenerate file in current preferred format -------------------------
    file_ext = prefs["last_file_format"]
    file_path = FileGenerator.generate_file(formatted_text, file_ext)

    # Update cache --------------------------------------------------------
    context.user_data["formatted_text"] = formatted_text
    context.user_data["file_path"] = file_path
    context.user_data["file_ext"] = file_ext
    context.user_data["metrics"] = metrics

    # Edit the main status message ----------------------------------------
    ready = _ready_text(
        title=transcript_data.get("title", "Untitled"),
        duration_s=transcript_data.get("duration_seconds", 0),
        word_count=metrics["word_count"],
        reading_time_s=metrics["reading_time_seconds"],
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

async def _handle_new_link(query, context: ContextTypes.DEFAULT_TYPE):
    await query.answer()

    # Clear extraction cache but keep user preferences --------------------
    for key in ("transcript_data", "formatted_text", "file_path",
                "file_ext", "video_id", "status_msg_id", "metrics",
                "url", "platform", "preview_msg_id"):
        context.user_data.pop(key, None)

    await query.edit_message_text("Transcript Flow\n\nSend a YouTube or Vimeo link.")


# ---------------------------------------------------------------------------
# Bot entry point
# ---------------------------------------------------------------------------

def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is polling...")
    application.run_polling()


if __name__ == "__main__":
    run_bot()
