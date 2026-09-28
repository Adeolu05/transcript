"""
Standalone cleanup script — run as a cron job when it shares storage with the API.

Usage:
    python -m app.cleanup

Primary cleanup for multi-service PaaS is in-process (see app.main lifespan).
Use this script when FILE_STORAGE_DIR points at a shared/persistent volume
visible to both the web service and the cron job.

Deletes all files in the file storage directory older than FILE_TTL_HOURS.
Covers base .txt files, converted .pdf/.docx/.srt/.vtt, and sidecars.
Also prunes transcript cache entries older than TRANSCRIPT_CACHE_TTL_HOURS.
"""

from app.services.file_service import TEMP_DIR, FileGenerator
from app.core.config import settings
from app.services.transcript_cache_service import prune_transcript_cache
from app.utils.logging_config import logger


def main() -> None:
    logger.info(
        "Cleanup cron: removing files older than %sh from %s",
        settings.file_ttl_hours,
        TEMP_DIR,
    )
    deleted = FileGenerator.cleanup_old_files(max_age_hours=settings.file_ttl_hours)
    pruned = prune_transcript_cache()
    logger.info(
        "Cleanup cron: done, deleted %s file(s), pruned %s cache entr(ies).", deleted, pruned
    )


if __name__ == "__main__":
    main()
