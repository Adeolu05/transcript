"""Tests for unified URL routing in transcript_service."""

import unittest
from unittest.mock import patch

from app.services.transcript_service import get_transcript_from_url


class TestGetTranscriptFromUrl(unittest.TestCase):
    @patch("app.services.transcript_service.write_transcript_cache")
    @patch("app.services.transcript_service.read_transcript_cache", return_value=None)
    @patch("app.services.transcript_service.get_youtube_transcript")
    def test_youtube_delegates(self, mock_yt, _mock_read, _mock_write):
        mock_yt.return_value = {
            "provider": "youtube",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "video_id": "dQw4w9WgXcQ",
            "title": "Test",
            "language": "en",
            "duration_seconds": 10,
            "segments": [{"text": "hi", "start": 0.0, "duration": 1.0}],
        }
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = get_transcript_from_url(url)
        mock_yt.assert_called_once()
        call_kw = mock_yt.call_args
        self.assertEqual(call_kw[0][0], "dQw4w9WgXcQ")
        self.assertEqual(call_kw[1].get("url"), url)
        self.assertEqual(result["provider"], "youtube")
        self.assertEqual(result["video_id"], "dQw4w9WgXcQ")

    @patch("app.services.transcript_service.write_transcript_cache")
    @patch("app.services.transcript_service.read_transcript_cache", return_value=None)
    @patch("app.services.transcript_service.get_vimeo_transcript")
    def test_vimeo_delegates(self, mock_vm, _mock_read, _mock_write):
        mock_vm.return_value = {
            "provider": "vimeo",
            "source_url": "https://vimeo.com/999",
            "video_id": "999",
            "title": "Vimeo test",
            "language": "en",
            "duration_seconds": 5,
            "segments": [],
        }
        url = "https://vimeo.com/999"
        result = get_transcript_from_url(url, deadline=123.0)
        mock_vm.assert_called_once_with("999", url=url, deadline=123.0)
        self.assertEqual(result["provider"], "vimeo")

    @patch("app.services.transcript_service.get_youtube_transcript")
    @patch("app.services.transcript_service.write_transcript_cache")
    def test_youtube_cache_hit_skips_fetch(self, _mock_write, mock_yt):
        cached = {
            "provider": "youtube",
            "source_url": "",
            "video_id": "cachedid123",
            "title": "From cache",
            "language": "en",
            "duration_seconds": 9,
            "segments": [],
        }
        with patch(
            "app.services.transcript_service.read_transcript_cache",
            return_value=dict(cached),
        ):
            url = "https://www.youtube.com/watch?v=cachedid123"
            result = get_transcript_from_url(url)
        mock_yt.assert_not_called()
        self.assertEqual(result["title"], "From cache")
        self.assertEqual(result["source_url"], url)

    def test_unsupported_platform_raises(self):
        with self.assertRaises(Exception) as ctx:
            get_transcript_from_url("https://example.com/video/1")
        self.assertIn("Unsupported", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
