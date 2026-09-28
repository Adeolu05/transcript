"""File-backed transcript cache (TTL) to cut repeat YouTube/Vimeo fetches."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def cache_dir() -> Path:
    raw = (settings.transcript_cache_dir or "").strip()
    if raw:
        return Path(raw)
    return _project_root() / "data" / "transcript_cache"


def _safe_video_stem(video_id: str) -> str:
    s = "".join(c for c in video_id if c.isalnum() or c in "_-")[:128]
    return s or "invalid"


def cache_path(provider: str, video_id: str, language: str = "en") -> Path:
    # Language is part of the key: the same video yields different captions per target
    return cache_dir() / f"{provider}_{_safe_video_stem(video_id)}_{_safe_video_stem(language)}.json"


def read_transcript_cache(
    provider: str, video_id: str, language: str = "en"
) -> Optional[Dict[str, Any]]:
    if not settings.transcript_cache_enabled:
        return None
    path = cache_path(provider, video_id, language)
    if not path.is_file():
        return None
    ttl_sec = max(0, int(settings.transcript_cache_ttl_hours * 3600))
    if ttl_sec and (time.time() - path.stat().st_mtime) > ttl_sec:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def write_transcript_cache(
    provider: str, video_id: str, data: Dict[str, Any], language: str = "en"
) -> None:
    if not settings.transcript_cache_enabled:
        return
    path = cache_path(provider, video_id, language)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        tmp.replace(path)
    except OSError:
        try:
            if tmp.is_file():
                tmp.unlink()
        except OSError:
            pass


def prune_transcript_cache() -> int:
    """
    Delete cache entries older than the TTL (plus stale .tmp leftovers).
    Reads already ignore expired entries; this keeps the directory from growing
    forever and caption text from outliving the advertised retention.
    TTL 0 means entries never expire, so nothing is pruned.
    """
    ttl_sec = max(0, int(settings.transcript_cache_ttl_hours * 3600))
    directory = cache_dir()
    if not ttl_sec or not directory.is_dir():
        return 0

    now = time.time()
    deleted = 0
    for path in directory.glob("*.json*"):
        try:
            if path.is_file() and now - path.stat().st_mtime > ttl_sec:
                path.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted
