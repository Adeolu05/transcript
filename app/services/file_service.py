import html
import json
import re
import time
import unicodedata
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

from docx import Document

from app.core.config import settings
from app.services.pdf_fonts import pdf_font_for
from app.utils.logging_config import logger


def resolve_temp_dir() -> Path:
    """
    Writable directory for generated TXT/PDF/DOCX and .raw sidecars.

    Default: <project>/data/tmp so Docker Compose volume `transcript_data`
    (mounted at /app/data) is shared by API + optional bot, and survives
    restarts better than container /tmp. Override with FILE_STORAGE_DIR.
    """
    path = settings.resolved_file_storage_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


# Resolved once at import; process restarts pick up env changes.
TEMP_DIR = resolve_temp_dir()


_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]+')
_MAX_FILENAME_STEM = 80


def download_filename(title: str | None, extension: str) -> str:
    """
    Human filename for a download, e.g. "My Talk.pdf". Strips path separators,
    control and reserved characters; falls back to "transcript".
    """
    stem = _UNSAFE_FILENAME_CHARS.sub(" ", title or "")
    stem = " ".join(stem.split()).strip(" .")[:_MAX_FILENAME_STEM].rstrip(" .")
    return f"{stem or 'transcript'}.{extension.lstrip('.')}"


def content_disposition(filename: str) -> str:
    """Attachment header with an ASCII fallback plus RFC 5987 UTF-8 name."""
    ascii_name = (
        unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    )
    ascii_name = ascii_name.replace('"', "").strip() or "transcript"
    if "." not in ascii_name.lstrip("."):
        ascii_name = f"transcript{Path(filename).suffix}"
    return (
        f'attachment; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


def write_sidecar(file_id: str, suffix: str, data: Any) -> None:
    """JSON sidecar next to a generated file (never downloadable: see _validate_file_id)."""
    (TEMP_DIR / f"{file_id}.{suffix}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def read_sidecar(file_id: str, suffix: str) -> Any | None:
    path = TEMP_DIR / f"{file_id}.{suffix}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class FileGenerator:
    @staticmethod
    def _get_temp_filepath(extension: str) -> Path:
        """Generates a unique temporary file path."""
        filename = f"{uuid.uuid4().hex}.{extension}"
        # Re-resolve in case dir was deleted
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return TEMP_DIR / filename

    @staticmethod
    def generate_txt(content: str, extension: str = "txt") -> str:
        filepath = FileGenerator._get_temp_filepath(extension)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return str(filepath)

    @staticmethod
    def generate_docx(content: str) -> str:
        filepath = FileGenerator._get_temp_filepath("docx")
        doc = Document()

        for paragraph in content.split("\n\n"):
            doc.add_paragraph(paragraph)

        doc.save(str(filepath))
        return str(filepath)

    @staticmethod
    def generate_pdf(content: str, language: str = "") -> str:
        """Raises pdf_fonts.UnsupportedPdfScript for scripts ReportLab can't typeset."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib.units import inch

        # Pick the font before creating the file so an unsupported script leaves nothing behind
        font = pdf_font_for(content, language)
        if font.drop:
            content = "".join(ch for ch in content if ch not in font.drop)

        filepath = FileGenerator._get_temp_filepath("pdf")

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        story = []
        styles = getSampleStyleSheet()
        style = styles["BodyText"].clone("Transcript", fontName=font.name)
        if font.cjk_wrap:
            style.wordWrap = "CJK"

        for para_text in content.split("\n\n"):
            if para_text.strip():
                para_text = para_text.replace("\n", " ")
                para_text = html.escape(para_text)
                story.append(Paragraph(para_text, style))
                story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        return str(filepath)

    @staticmethod
    def generate_file(content: str, file_format: str, language: str = "") -> str:
        """Returns the absolute path to the generated file on disk."""
        if file_format == "docx":
            return FileGenerator.generate_docx(content)
        if file_format == "pdf":
            return FileGenerator.generate_pdf(content, language)
        if file_format in ("srt", "vtt"):
            return FileGenerator.generate_txt(content, file_format)
        return FileGenerator.generate_txt(content)

    @staticmethod
    def cleanup_old_files(max_age_hours: int | None = None) -> int:
        """Deletes files in TEMP_DIR older than max_age_hours. Returns count deleted."""
        age_h = settings.file_ttl_hours if max_age_hours is None else max_age_hours
        now = time.time()
        max_age_seconds = max(0, float(age_h)) * 3600
        deleted = 0

        storage = resolve_temp_dir()
        if not storage.is_dir():
            return 0

        for file_path in storage.glob("*.*"):
            if not file_path.is_file():
                continue
            try:
                file_mtime = file_path.stat().st_mtime
                if now - file_mtime > max_age_seconds:
                    file_path.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning("Failed to delete old file %s: %s", file_path, e)

        return deleted
