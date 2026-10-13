"""Tests must never write to the developer's real data/ folder (metrics.db in particular)."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import analytics_service
from app.services.file_service import TEMP_DIR
from app.services.rate_limit_service import rate_limiter
from app.services.transcript_cache_service import cache_dir

_REAL_DB = analytics_service._DEFAULT_DB_PATH
_TMP_ROOT = Path(tempfile.gettempdir()).resolve()


def _real_row_count():
    """Row count of the real metrics.db, read-only (never creates it); None if absent."""
    if not _REAL_DB.is_file():
        return None
    conn = sqlite3.connect(f"file:{_REAL_DB.as_posix()}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()


class TestIsolation(unittest.TestCase):
    def test_stores_point_at_temp_directory(self):
        for path in (analytics_service.metrics_db_path(), TEMP_DIR, cache_dir()):
            self.assertTrue(
                Path(path).resolve().is_relative_to(_TMP_ROOT),
                f"{path} is outside the temp dir: run tests with `-t .` so tests/__init__.py loads",
            )

    def test_extract_does_not_touch_real_metrics_db(self):
        rate_limiter._store.clear()
        before = _real_row_count()
        with patch("app.api.v1_routes.get_transcript_from_url") as fetch:
            fetch.return_value = {
                "provider": "youtube", "video_id": "testvideo12", "title": "T",
                "language": "en", "duration_seconds": 10,
                "segments": [{"text": "hi", "start": 0.0, "duration": 1.0}],
            }
            r = TestClient(app).post(
                "/api/v1/extract", json={"url": "https://www.youtube.com/watch?v=testvideo12"}
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(_real_row_count(), before)

        conn = sqlite3.connect(analytics_service.metrics_db_path())
        try:
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
