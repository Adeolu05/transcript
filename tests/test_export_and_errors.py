"""Tests for SRT/VTT export, download filenames, cache pruning, and typed fetch errors."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from youtube_transcript_api import AgeRestricted

from app.core.errors import ErrorCode, TranscriptFetchError
from app.services import transcript_cache_service as tcs
from app.services.file_service import content_disposition, download_filename
from app.services.formatter_service import TranscriptFormatter
from app.services.transcript_service import get_youtube_transcript
from app.services.vimeo_service import get_vimeo_transcript

_SEGMENTS = [
    {"text": "Hello >> there", "start": 0.0, "duration": 3.0},  # overlaps next cue
    {"text": "   ", "start": 1.5, "duration": 1.0},  # blank: skipped
    {"text": "second", "start": 2.0, "duration": 1.0},
    {"text": "last", "start": 3661.25, "duration": 0.0},  # zero-length: floored
]


class TestSubtitleFormats(unittest.TestCase):
    def test_srt(self):
        out = TranscriptFormatter.format_srt(_SEGMENTS)
        self.assertEqual(
            out,
            "1\n00:00:00,000 --> 00:00:02,000\nHello there\n"
            "\n2\n00:00:02,000 --> 00:00:03,000\nsecond\n"
            "\n3\n01:01:01,250 --> 01:01:01,750\nlast\n",
        )

    def test_vtt(self):
        out = TranscriptFormatter.format_vtt(_SEGMENTS)
        self.assertTrue(out.startswith("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello there\n"))
        self.assertIn("01:01:01.250 --> 01:01:01.750\nlast\n", out)

    def test_blank_lines_inside_cue_removed(self):
        out = TranscriptFormatter.format_srt(
            [{"text": "line one\n\n  line   two ", "start": 0, "duration": 1}]
        )
        self.assertEqual(out, "1\n00:00:00,000 --> 00:00:01,000\nline one\nline two\n")

    def test_unknown_subtitle_format_rejected(self):
        with self.assertRaises(ValueError):
            TranscriptFormatter.format_subtitles(_SEGMENTS, "pdf")


class TestDownloadFilename(unittest.TestCase):
    def test_uses_title(self):
        self.assertEqual(download_filename("My Talk", ".pdf"), "My Talk.pdf")

    def test_strips_unsafe_characters(self):
        self.assertEqual(
            download_filename('../etc/pass"wd: a|b?', "txt"), "etc pass wd a b.txt"
        )

    def test_falls_back_when_empty(self):
        self.assertEqual(download_filename(None, "srt"), "transcript.srt")
        self.assertEqual(download_filename(" ... ", "srt"), "transcript.srt")

    def test_truncates_long_titles(self):
        self.assertEqual(download_filename("x" * 300, "txt"), "x" * 80 + ".txt")

    def test_content_disposition_non_ascii(self):
        header = content_disposition("Café 日本.pdf")
        self.assertIn('filename="Cafe .pdf"', header)
        self.assertIn("filename*=UTF-8''Caf%C3%A9%20%E6%97%A5%E6%9C%AC.pdf", header)

    def test_content_disposition_all_non_ascii_falls_back(self):
        self.assertIn('filename="transcript.pdf"', content_disposition("日本.pdf"))


class TestPruneTranscriptCache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _file(self, name: str, age_seconds: float) -> Path:
        path = self.dir / name
        path.write_text("{}", encoding="utf-8")
        t = time.time() - age_seconds
        os.utime(path, (t, t))
        return path

    def test_deletes_only_expired_entries(self):
        old = self._file("youtube_old.json", 3 * 3600)
        stale_tmp = self._file("youtube_x.json.tmp", 3 * 3600)
        fresh = self._file("youtube_new.json", 60)
        with patch.object(tcs.settings, "transcript_cache_ttl_hours", 1), patch.object(
            tcs.settings, "transcript_cache_dir", str(self.dir)
        ):
            self.assertEqual(tcs.prune_transcript_cache(), 2)
        self.assertFalse(old.exists())
        self.assertFalse(stale_tmp.exists())
        self.assertTrue(fresh.exists())

    def test_ttl_zero_never_prunes(self):
        old = self._file("youtube_old.json", 10**7)
        with patch.object(tcs.settings, "transcript_cache_ttl_hours", 0), patch.object(
            tcs.settings, "transcript_cache_dir", str(self.dir)
        ):
            self.assertEqual(tcs.prune_transcript_cache(), 0)
        self.assertTrue(old.exists())


class TestTypedFetchErrors(unittest.TestCase):
    @patch("app.services.transcript_service._youtube_transcript_fresh_core")
    def test_unmapped_library_error_is_typed(self, mock_core):
        mock_core.side_effect = AgeRestricted("vid")
        with self.assertRaises(TranscriptFetchError) as ctx:
            get_youtube_transcript("vid")
        self.assertEqual(ctx.exception.code, ErrorCode.TRANSCRIPT_NOT_AVAILABLE)
        self.assertEqual(
            ctx.exception.message, "Captions could not be retrieved for this video."
        )

    @patch("app.services.vimeo_service.requests.get")
    def test_vimeo_private_video(self, mock_get):
        resp = MagicMock(status_code=403)
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError(response=resp)
        with self.assertRaises(TranscriptFetchError) as ctx:
            get_vimeo_transcript("12345")
        self.assertIn("private or restricted", ctx.exception.message)

    @patch("app.services.vimeo_service.requests.get")
    def test_vimeo_no_text_tracks(self, mock_get):
        mock_get.return_value.text = "<title>Clip on Vimeo</title>"
        with self.assertRaises(TranscriptFetchError) as ctx:
            get_vimeo_transcript("12345")
        self.assertEqual(ctx.exception.code, ErrorCode.TRANSCRIPT_NOT_AVAILABLE)


if __name__ == "__main__":
    unittest.main()
