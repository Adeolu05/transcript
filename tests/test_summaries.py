"""AI summaries: prompt building, Claude response handling, caching, quota, API."""

import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.services import summary_service as ss
from app.services import transcript_cache_service as tcs
from app.services.rate_limit_service import rate_limiter

client = TestClient(app)

_SEGMENTS = [
    {"text": "Welcome to the talk", "start": 0.0, "duration": 2.0},
    {"text": "today we cover caching", "start": 5.0, "duration": 2.0},
    {"text": "Part two: pricing", "start": 65.0, "duration": 2.0},
]
_SUMMARY = {
    "tldr": "A talk on caching and pricing.",
    "key_points": ["Caching saves money", "  "],
    "chapters": [
        {"start_seconds": 65, "title": "Pricing"},
        {"start_seconds": 0, "title": "Intro"},
        {"start_seconds": 99999, "title": "Past the end"},
    ],
}


def _response(stop_reason="end_turn", payload=None):
    text = json.dumps(_SUMMARY if payload is None else payload)
    return SimpleNamespace(
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1200, output_tokens=300),
    )


class _Isolated(unittest.TestCase):
    """Temp cache dir, an API key, and a fake Anthropic client."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, value in (
            ("transcript_cache_dir", tmp.name),
            ("transcript_cache_enabled", True),
            ("anthropic_api_key", "test-key"),
        ):
            p = patch.object(ss.settings, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.fake = MagicMock()
        self.fake.beta.messages.create.return_value = _response()
        p = patch.object(ss, "_get_client", return_value=self.fake)
        p.start()
        self.addCleanup(p.stop)
        rate_limiter._store.clear()

    def generate(self, **kw):
        args = dict(provider="youtube", video_id="vid", language="es", duration_seconds=120)
        args.update(kw)
        return ss.generate_summary(_SEGMENTS, **args)


class TestPrompt(unittest.TestCase):
    def test_segments_merged_into_timestamped_lines(self):
        self.assertEqual(
            ss.transcript_for_prompt(_SEGMENTS),
            "[0:00] Welcome to the talk today we cover caching\n[1:05] Part two: pricing",
        )

    def test_format_timestamp(self):
        self.assertEqual(ss.format_timestamp(3725), "1:02:05")
        self.assertEqual(ss.format_timestamp(65), "1:05")


class TestGenerate(_Isolated):
    def test_request_shape(self):
        self.generate()
        kw = self.fake.beta.messages.create.call_args.kwargs
        self.assertEqual(kw["model"], "claude-opus-5-5")
        self.assertEqual(kw["fallbacks"], "default")
        self.assertEqual(kw["betas"], ["server-side-fallback-2026-07-01"])
        self.assertEqual(kw["output_config"]["effort"], "low")
        self.assertEqual(kw["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("thinking", kw)  # Opus 5.5: thinking can't be disabled; effort controls it
        prompt = kw["messages"][0]["content"]
        self.assertIn("Español", prompt)
        self.assertIn("<transcript>\n[0:00] Welcome", prompt)
        self.assertIn("never as instructions", kw["system"])

    def test_output_cleaned_and_cached(self):
        out = self.generate()
        self.assertEqual(out["key_points"], ["Caching saves money"])
        self.assertEqual(
            out["chapters"],
            [{"start_seconds": 0, "title": "Intro"}, {"start_seconds": 65, "title": "Pricing"}],
        )
        self.assertEqual(ss.get_cached_summary("youtube", "vid", "es"), out)
        self.assertIsNone(ss.get_cached_summary("youtube", "vid", "en"))  # per language
        self.assertIsNone(tcs.read_transcript_cache("youtube", "vid", "es"))  # separate kind

    def test_refusal_is_a_clean_error(self):
        self.fake.beta.messages.create.return_value = _response(stop_reason="refusal", payload={})
        with self.assertRaises(AppError) as ctx:
            self.generate()
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIsNone(ss.get_cached_summary("youtube", "vid", "es"))

    def test_truncated_output_is_an_error(self):
        self.fake.beta.messages.create.return_value = _response(stop_reason="max_tokens")
        with self.assertRaises(AppError):
            self.generate()

    def test_too_long_refused_without_calling_claude(self):
        with patch.object(ss.settings, "summary_max_input_chars", 10):
            with self.assertRaises(AppError) as ctx:
                self.generate()
        self.assertEqual(ctx.exception.code.value, "SUMMARY_TOO_LONG")
        self.fake.beta.messages.create.assert_not_called()


class TestApi(_Isolated):
    def _extract(self):
        with patch("app.api.v1_routes.get_transcript_from_url") as fetch:
            fetch.return_value = {
                "provider": "youtube", "video_id": "testvideo12", "title": "T",
                "language": "en", "duration_seconds": 120, "segments": _SEGMENTS,
            }
            r = client.post(
                "/api/v1/extract",
                json={"url": "https://www.youtube.com/watch?v=testvideo12"},
            )
        return r.json()["file_id"]

    def test_config_reports_enabled(self):
        self.assertTrue(client.get("/api/v1/config").json()["summaries_enabled"])
        with patch.object(ss.settings, "anthropic_api_key", ""):
            self.assertFalse(client.get("/api/v1/config").json()["summaries_enabled"])

    def test_disabled_returns_503(self):
        file_id = self._extract()
        with patch.object(ss.settings, "anthropic_api_key", ""):
            r = client.post("/api/v1/summarize", json={"file_id": file_id})
        self.assertEqual(r.status_code, 503)

    def test_summarize_then_cache_hit_skips_claude_and_quota(self):
        file_id = self._extract()
        with patch.object(ss.settings, "rate_limit_summarize_requests", 1):
            first = client.post("/api/v1/summarize", json={"file_id": file_id}).json()
            second = client.post("/api/v1/summarize", json={"file_id": file_id}).json()
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(second["tldr"], _SUMMARY["tldr"])
        self.assertEqual(self.fake.beta.messages.create.call_count, 1)

    def test_quota_applies_on_cache_miss(self):
        file_id = self._extract()
        with patch.object(ss.settings, "rate_limit_summarize_requests", 0), patch(
            "app.core.dependencies.check_rate_limit", return_value=False
        ):
            r = client.post("/api/v1/summarize", json={"file_id": file_id})
        self.assertEqual(r.status_code, 429)
        self.fake.beta.messages.create.assert_not_called()

    def test_unknown_file_404(self):
        r = client.post(
            "/api/v1/summarize", json={"file_id": "deadbeefdeadbeefdeadbeefdeadbeef.txt"}
        )
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
