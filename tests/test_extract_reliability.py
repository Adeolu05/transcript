"""Tests for extract time budget: concurrent metadata, deadlines, IP-block reporting."""

import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from fastapi.testclient import TestClient
from youtube_transcript_api import IpBlocked

from app.core.errors import ErrorCode, TranscriptFetchError
from app.main import app
from app.services.rate_limit_service import rate_limiter
from app.services import transcript_service as ts
from app.services.vimeo_service import get_vimeo_transcript

client = TestClient(app)


class _Fetched(list):
    language_code = "en"


def _mock_api(on_list=None):
    """YouTubeTranscriptApi stand-in whose list() returns one English track."""
    tr = MagicMock(language_code="en", is_translatable=False)
    tr.fetch.return_value = _Fetched([SimpleNamespace(text="hi", start=0.0, duration=1.0)])
    tlist = MagicMock()
    tlist.find_transcript.return_value = tr

    def _list(_video_id):
        if on_list:
            on_list()
        return tlist

    api = MagicMock()
    api.list.side_effect = _list
    return api


class TestConcurrentMetadata(unittest.TestCase):
    def test_title_fetch_overlaps_caption_fetch(self):
        captions_started = threading.Event()

        def metadata(_vid):
            # Only succeeds if it runs while captions are being fetched
            if not captions_started.wait(timeout=1):
                return {"title": "SEQUENTIAL", "duration": 0}
            return {"title": "Concurrent", "duration": 0}

        with patch.object(ts, "_get_youtube_metadata", side_effect=metadata), patch.object(
            ts, "YouTubeTranscriptApi", return_value=_mock_api(captions_started.set)
        ):
            result = ts.get_youtube_transcript("vid")
        self.assertEqual(result["title"], "Concurrent")

    def test_slow_title_does_not_hold_captions(self):
        release = threading.Event()
        self.addCleanup(release.set)

        def metadata(_vid):
            release.wait(timeout=5)
            return {"title": "Late", "duration": 0}

        with patch.object(ts, "_get_youtube_metadata", side_effect=metadata), patch.object(
            ts, "YouTubeTranscriptApi", return_value=_mock_api()
        ), patch.object(ts, "_METADATA_GRACE_SECONDS", 0.05):
            started = time.monotonic()
            result = ts.get_youtube_transcript("vid")
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(result["title"], "YouTube Video vid")
        self.assertEqual(result["segments"][0]["text"], "hi")


class TestOembedMetadata(unittest.TestCase):
    @patch("app.services.transcript_service.requests.get")
    def test_title_from_oembed(self, mock_get):
        mock_get.return_value.json.return_value = {"title": "Tom & Jerry"}
        self.assertEqual(
            ts._get_youtube_metadata("vid"), {"title": "Tom & Jerry", "duration": 0}
        )

    @patch("app.services.transcript_service.requests.get")
    def test_fallback_on_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError()
        self.assertEqual(ts._get_youtube_metadata("vid")["title"], "YouTube Video vid")


class TestDeadline(unittest.TestCase):
    def test_session_refuses_requests_after_deadline(self):
        session = ts._DeadlineSession(time.monotonic() - 1)
        with self.assertRaises(ts._DeadlineExceeded):
            session.get("https://example.invalid")

    def test_session_caps_request_timeout(self):
        session = ts._DeadlineSession(time.monotonic() + 2)
        with patch("requests.Session.request") as mock_request:
            session.get("https://example.invalid", timeout=30)
        self.assertLessEqual(mock_request.call_args.kwargs["timeout"], 2)

    @patch("app.services.transcript_service.time.sleep")
    @patch("app.services.transcript_service._youtube_ip_block_attempts", return_value=5)
    @patch("app.services.transcript_service._youtube_transcript_fresh_core")
    def test_no_retry_sleep_past_deadline(self, mock_core, _attempts, mock_sleep):
        mock_core.side_effect = IpBlocked("vid")
        with self.assertRaises(TranscriptFetchError) as ctx:
            ts.get_youtube_transcript("vid", deadline=time.monotonic() + 0.1)
        mock_sleep.assert_not_called()
        self.assertEqual(mock_core.call_count, 1)
        self.assertEqual(ctx.exception.code, ErrorCode.UPSTREAM_BLOCKED)

    @patch("app.services.transcript_service._youtube_transcript_fresh_core")
    def test_deadline_exceeded_is_upstream_timeout(self, mock_core):
        mock_core.side_effect = ts._DeadlineExceeded()
        with self.assertRaises(TranscriptFetchError) as ctx:
            ts.get_youtube_transcript("vid", deadline=time.monotonic())
        self.assertEqual(ctx.exception.code, ErrorCode.UPSTREAM_TIMEOUT)
        self.assertEqual(ctx.exception.status_code, 504)

    @patch("app.services.vimeo_service.requests.get")
    def test_vimeo_stops_after_deadline(self, mock_get):
        with self.assertRaises(TranscriptFetchError) as ctx:
            get_vimeo_transcript("123", deadline=time.monotonic() - 1)
        self.assertEqual(ctx.exception.code, ErrorCode.UPSTREAM_TIMEOUT)
        mock_get.assert_not_called()


class TestBlockedResponse(unittest.TestCase):

    def setUp(self):
        # All TestClient requests share one "IP"; other suites' extracts must not exhaust its quota
        rate_limiter._store.clear()
    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_ip_block_returns_503_with_own_code(self, mock_fetch):
        mock_fetch.side_effect = ts._youtube_fetch_error(IpBlocked("vid"))
        r = client.post(
            "/api/v1/extract",
            json={"url": "https://www.youtube.com/watch?v=testvideo12", "include_timestamps": False},
        )
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"]["code"], "UPSTREAM_BLOCKED")
        self.assertIn("blocked this server", r.json()["error"]["message"])

    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_api_passes_deadline_within_budget(self, mock_fetch):
        mock_fetch.side_effect = TranscriptFetchError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE, "x")
        before = time.monotonic()
        client.post(
            "/api/v1/extract",
            json={"url": "https://www.youtube.com/watch?v=testvideo12", "include_timestamps": False},
        )
        deadline = mock_fetch.call_args.args[1]
        self.assertGreater(deadline, before)
        self.assertLessEqual(deadline, time.monotonic() + ts.settings.transcript_timeout_seconds)


if __name__ == "__main__":
    unittest.main()
