"""
Lightweight persistent event store for operational metrics.
Uses SQLite — survives restarts, zero external dependencies.
"""

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.utils.logging_config import logger

# ---------------------------------------------------------------------------
# Database location
# ---------------------------------------------------------------------------
_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "metrics.db"

# Thread-local storage for connections (SQLite is not thread-safe by default)
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating the DB if needed."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _init_schema(_local.conn)
    return _local.conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp           TEXT    NOT NULL,
            success             INTEGER NOT NULL,
            source              TEXT    NOT NULL,
            format              TEXT,
            provider            TEXT,
            duration_seconds    INTEGER,
            processing_time_ms  INTEGER,
            error_code          TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class AnalyticsService:
    """Thin wrapper around the SQLite event store."""

    @staticmethod
    def record_event(
        *,
        success: bool,
        source: str,
        fmt: Optional[str] = None,
        provider: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """Insert one event row."""
        try:
            conn = _get_conn()
            conn.execute(
                """
                INSERT INTO events
                    (timestamp, success, source, format, provider,
                     duration_seconds, processing_time_ms, error_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    1 if success else 0,
                    source,
                    fmt,
                    provider,
                    duration_seconds,
                    processing_time_ms,
                    error_code,
                ),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Analytics record_event error: {e}")

    @staticmethod
    def get_summary(hours: int = 24) -> Dict[str, Any]:
        """Aggregate stats for the last *hours* hours."""
        try:
            conn = _get_conn()
            cutoff = datetime.now(timezone.utc).isoformat()
            # SQLite datetime comparison works on ISO strings
            cur = conn.execute(
                """
                SELECT
                    COUNT(*)                                    AS total,
                    SUM(success)                                AS successes,
                    AVG(CASE WHEN success=1 THEN processing_time_ms END) AS avg_ms
                FROM events
                WHERE timestamp >= datetime('now', ?)
                """,
                (f"-{hours} hours",),
            )
            row = cur.fetchone()
            total = row["total"] or 0
            successes = row["successes"] or 0
            avg_ms = round(row["avg_ms"] or 0)

            # Error distribution
            err_rows = conn.execute(
                """
                SELECT error_code, COUNT(*) AS cnt
                FROM events
                WHERE timestamp >= datetime('now', ?) AND success = 0
                GROUP BY error_code
                ORDER BY cnt DESC
                """,
                (f"-{hours} hours",),
            ).fetchall()
            errors = {r["error_code"]: r["cnt"] for r in err_rows}

            # Format distribution
            fmt_rows = conn.execute(
                """
                SELECT format, COUNT(*) AS cnt
                FROM events
                WHERE timestamp >= datetime('now', ?) AND success = 1
                GROUP BY format
                ORDER BY cnt DESC
                """,
                (f"-{hours} hours",),
            ).fetchall()
            formats = {r["format"]: r["cnt"] for r in fmt_rows}

            # Rate limit hits (error_code = 'RATE_LIMIT_EXCEEDED')
            rl_row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM events
                WHERE timestamp >= datetime('now', ?) AND error_code = 'RATE_LIMIT_EXCEEDED'
                """,
                (f"-{hours} hours",),
            ).fetchone()
            rate_limit_hits = rl_row["cnt"] if rl_row else 0

            # Source distribution
            src_rows = conn.execute(
                """
                SELECT source, COUNT(*) AS cnt
                FROM events
                WHERE timestamp >= datetime('now', ?)
                GROUP BY source
                ORDER BY cnt DESC
                """,
                (f"-{hours} hours",),
            ).fetchall()
            sources = {r["source"]: r["cnt"] for r in src_rows}

            return {
                "total": total,
                "successes": successes,
                "failures": total - successes,
                "success_rate": round((successes / total * 100), 1) if total else 0,
                "avg_processing_time_ms": avg_ms,
                "error_distribution": errors,
                "format_distribution": formats,
                "source_distribution": sources,
                "rate_limit_hits": rate_limit_hits,
            }
        except Exception as e:
            logger.error(f"Analytics get_summary error: {e}")
            return {
                "total": 0, "successes": 0, "failures": 0,
                "success_rate": 0, "avg_processing_time_ms": 0,
                "error_distribution": {}, "format_distribution": {},
                "source_distribution": {}, "rate_limit_hits": 0,
            }
