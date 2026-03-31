"""Tests for file-backed transcript cache."""

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import transcript_cache_service as tcs


class TestTranscriptCacheService(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_write_read_roundtrip(self):
        payload = {
            "provider": "youtube",
            "video_id": "abc123xyz01",
            "title": "T",
            "segments": [{"text": "hi", "start": 0.0, "duration": 1.0}],
        }
        with patch.object(tcs.settings, "transcript_cache_enabled", True), patch.object(
            tcs.settings, "transcript_cache_ttl_hours", 72
        ), patch.object(tcs.settings, "transcript_cache_dir", str(self.dir)):
            tcs.write_transcript_cache("youtube", "abc123xyz01", payload)
            got = tcs.read_transcript_cache("youtube", "abc123xyz01")
        self.assertEqual(got, payload)

    def test_expired_returns_none(self):
        path = self.dir / "youtube_vid.json"
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"provider": "youtube", "video_id": "vid"}, f)
        old = time.time() - 500_000
        Path(path).touch()
        # Force mtime into the past (best-effort across platforms)
        try:
            import os

            os.utime(path, (old, old))
        except OSError:
            self.skipTest("cannot set mtime for TTL test")

        with patch.object(tcs.settings, "transcript_cache_enabled", True), patch.object(
            tcs.settings, "transcript_cache_ttl_hours", 1
        ), patch.object(tcs.settings, "transcript_cache_dir", str(self.dir)):
            got = tcs.read_transcript_cache("youtube", "vid")
        self.assertIsNone(got)

    def test_disabled_skips_read_write(self):
        with patch.object(tcs.settings, "transcript_cache_enabled", False), patch.object(
            tcs.settings, "transcript_cache_dir", str(self.dir)
        ):
            tcs.write_transcript_cache("youtube", "z", {"a": 1})
            p = tcs.cache_path("youtube", "z")
            self.assertFalse(p.is_file())
            self.assertIsNone(tcs.read_transcript_cache("youtube", "z"))


if __name__ == "__main__":
    unittest.main()
