"""
Standalone cleanup script — run as a Render cron job.

Usage:
    python -m app.cleanup

Deletes all files in TEMP_DIR older than FILE_TTL_HOURS.
Covers base .txt files, converted .pdf/.docx, and .raw sidecars.
"""

from app.services.file_service import FileGenerator
from app.core.config import settings
from app.utils.logging_config import logger


def main() -> None:
    logger.info(
        f"Cleanup cron: removing files older than {settings.file_ttl_hours}h"
    )
    deleted = FileGenerator.cleanup_old_files(
        max_age_hours=settings.file_ttl_hours
    )
    logger.info(f"Cleanup cron: done, deleted {deleted} file(s).")


if __name__ == "__main__":
    main()
