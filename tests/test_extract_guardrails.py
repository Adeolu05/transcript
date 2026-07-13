"""Guardrails: duration estimate, segment/size limits."""

import unittest
from unittest.mock import patch

from app.core.errors import AppError, ErrorCode
from app.services.extract_guardrails import (
    enforce_transcript_guardrails,
    estimate_duration_seconds,
)


class TestEstimateDuration(unittest.TestCase):
    def test_prefers_reported(self):
        data = {
            "duration_seconds": 120,
            "segments": [{"text": "a", "start": 0.0, "duration": 1.0}],
        }
        self.assertEqual(estimate_duration_seconds(data), 120)

    def test_estimates_from_last_segment(self):
        data = {
            "duration_seconds": 0,
            "segments": [
                {"text": "a", "start": 0.0, "duration": 1.0},
                {"text": "b", "start": 3500.0, "duration": 5.0},
            ],
        }
        self.assertEqual(estimate_duration_seconds(data), 3505)


class TestEnforceGuardrails(unittest.TestCase):
    def test_rejects_over_max_duration(self):
        data = {
            "video_id": "x",
            "duration_seconds": 20_000,
            "segments": [{"text": "hi", "start": 0.0, "duration": 1.0}],
        }
        with patch("app.services.extract_guardrails.settings") as s:
            s.max_video_duration_seconds = 10800
            s.max_transcript_segments = 20000
            s.max_raw_text_length = 500_000
            with self.assertRaises(AppError) as ctx:
                enforce_transcript_guardrails(data)
            self.assertEqual(ctx.exception.code, ErrorCode.VIDEO_TOO_LONG)

    def test_rejects_estimated_over_max(self):
        data = {
            "video_id": "x",
            "duration_seconds": 0,
            "segments": [{"text": "hi", "start": 20_000.0, "duration": 10.0}],
        }
        with patch("app.services.extract_guardrails.settings") as s:
            s.max_video_duration_seconds = 10800
            s.max_transcript_segments = 20000
            s.max_raw_text_length = 500_000
            with self.assertRaises(AppError) as ctx:
                enforce_transcript_guardrails(data)
            self.assertEqual(ctx.exception.code, ErrorCode.VIDEO_TOO_LONG)

    def test_rejects_too_many_segments(self):
        data = {
            "video_id": "x",
            "duration_seconds": 60,
            "segments": [{"text": "x", "start": float(i), "duration": 0.1} for i in range(50)],
        }
        with patch("app.services.extract_guardrails.settings") as s:
            s.max_video_duration_seconds = 10800
            s.max_transcript_segments = 10
            s.max_raw_text_length = 500_000
            with self.assertRaises(AppError) as ctx:
                enforce_transcript_guardrails(data)
            self.assertEqual(ctx.exception.code, ErrorCode.VIDEO_TOO_LONG)

    def test_allows_normal(self):
        data = {
            "video_id": "x",
            "duration_seconds": 120,
            "segments": [{"text": "hello", "start": 0.0, "duration": 1.0}],
        }
        with patch("app.services.extract_guardrails.settings") as s:
            s.max_video_duration_seconds = 10800
            s.max_transcript_segments = 20000
            s.max_raw_text_length = 500_000
            d = enforce_transcript_guardrails(data)
        self.assertEqual(d, 120)


if __name__ == "__main__":
    unittest.main()
