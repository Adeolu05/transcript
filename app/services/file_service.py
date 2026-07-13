import html
import time
import uuid
from pathlib import Path

from docx import Document

from app.core.config import settings
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


class FileGenerator:
    @staticmethod
    def _get_temp_filepath(extension: str) -> Path:
        """Generates a unique temporary file path."""
        filename = f"{uuid.uuid4().hex}.{extension}"
        # Re-resolve in case dir was deleted
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return TEMP_DIR / filename

    @staticmethod
    def generate_txt(content: str) -> str:
        filepath = FileGenerator._get_temp_filepath("txt")
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
    def generate_pdf(content: str) -> str:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib.units import inch

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
        style = styles["BodyText"]

        for para_text in content.split("\n\n"):
            if para_text.strip():
                para_text = para_text.replace("\n", " ")
                para_text = html.escape(para_text)
                story.append(Paragraph(para_text, style))
                story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        return str(filepath)

    @staticmethod
    def generate_file(content: str, file_format: str) -> str:
        """Returns the absolute path to the generated file on disk."""
        if file_format == "docx":
            return FileGenerator.generate_docx(content)
        if file_format == "pdf":
            return FileGenerator.generate_pdf(content)
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
