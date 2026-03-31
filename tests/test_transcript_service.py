import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.services.transcript_service import get_transcript, get_youtube_transcript
from youtube_transcript_api import TranscriptsDisabled, VideoUnavailable, IpBlocked


class _FetchedLike:
    def __init__(self, language_code: str, snippets):
        self.language_code = language_code
        self._snippets = snippets

    def __iter__(self):
        return iter(self._snippets)


class TestTranscriptService(unittest.TestCase):
    @patch("app.services.transcript_service.YouTubeTranscriptApi")
    @patch("app.services.transcript_service._get_youtube_metadata")
    def test_get_transcript_success_multi_lang_path(self, mock_meta, MockApiClass):
        mock_meta.return_value = {"title": "Test Title", "duration": 100}
        mock_api = MockApiClass.return_value
        mock_tr = MagicMock()
        mock_tr.language_code = "en"
        mock_tr.is_translatable = False
        mock_tr.fetch.return_value = _FetchedLike(
            "en",
            [SimpleNamespace(text="Hello", start=0.0, duration=1.0)],
        )
        mock_tlist = MagicMock()
        mock_tlist.find_transcript.return_value = mock_tr
        mock_api.list.return_value = mock_tlist

        result = get_transcript("test_video_id")

        mock_api.list.assert_called_once_with("test_video_id")
        mock_tlist.find_transcript.assert_called_once()
        mock_tr.fetch.assert_called_once()
        self.assertEqual(result["video_id"], "test_video_id")
        self.assertEqual(result["title"], "Test Title")
        self.assertEqual(result["duration_seconds"], 100)
        self.assertEqual(result["language"], "en")
        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(result["segments"][0]["text"], "Hello")

    @patch("app.services.transcript_service.YouTubeTranscriptApi")
    @patch("app.services.transcript_service._get_youtube_metadata")
    def test_get_transcript_explicit_languages_uses_list_find(self, mock_meta, MockApiClass):
        mock_meta.return_value = {"title": "T", "duration": 1}
        mock_api = MockApiClass.return_value
        mock_tr = MagicMock()
        mock_tr.language_code = "de"
        mock_tr.is_translatable = False
        mock_tr.fetch.return_value = _FetchedLike(
            "de",
            [SimpleNamespace(text="Hallo", start=0.0, duration=1.0)],
        )
        mock_tlist = MagicMock()
        mock_tlist.find_transcript.return_value = mock_tr
        mock_api.list.return_value = mock_tlist
        result = get_transcript("vid", languages=["de"])
        mock_api.list.assert_called_once_with("vid")
        mock_tlist.find_transcript.assert_called_once_with(("de",))
        mock_tr.fetch.assert_called_once()
        self.assertEqual(result["language"], "de")
        self.assertEqual(result["segments"][0]["text"], "Hallo")

    @patch("app.services.transcript_service._get_youtube_metadata")
    @patch("app.services.transcript_service.YouTubeTranscriptApi")
    def test_transcripts_disabled(self, MockApiClass, mock_meta):
        mock_meta.return_value = {"title": "Test", "duration": 0}
        MockApiClass.return_value.list.side_effect = TranscriptsDisabled("test_video_id")

        with self.assertRaises(Exception) as context:
            get_transcript("test_video_id")

        self.assertIn("Transcripts are disabled", str(context.exception))

    @patch("app.services.transcript_service._get_youtube_metadata")
    @patch("app.services.transcript_service.YouTubeTranscriptApi")
    def test_video_unavailable(self, MockApiClass, mock_meta):
        mock_meta.return_value = {"title": "Test", "duration": 0}
        MockApiClass.return_value.list.side_effect = VideoUnavailable("test_video_id")

        with self.assertRaises(Exception) as context:
            get_transcript("test_video_id")

        self.assertIn("Video is unavailable", str(context.exception))

    @patch("app.services.transcript_service.time.sleep")
    @patch("app.services.transcript_service._youtube_ip_block_attempts", return_value=3)
    @patch("app.services.transcript_service._youtube_transcript_fresh_core")
    def test_youtube_retries_then_success_on_ip_block(
        self, mock_core, _mock_attempts, mock_sleep
    ):
        ok = {
            "provider": "youtube",
            "source_url": "",
            "video_id": "vid",
            "title": "T",
            "language": "en",
            "duration_seconds": 1,
            "segments": [],
        }
        mock_core.side_effect = [IpBlocked("vid"), IpBlocked("vid"), ok]
        result = get_youtube_transcript("vid", url="")
        self.assertEqual(result, ok)
        self.assertEqual(mock_core.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
