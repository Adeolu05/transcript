"""AI cleanup + structured exports: prompt shape, Claude response handling, caching, quota, API."""

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.services import enhance_service as es
from app.services import summary_service as ss
from app.services import transcript_cache_service as tcs
from app.services.rate_limit_service import rate_limiter

client = TestClient(app)

_SEGMENTS = [
    {"text": "welcome to the show i am anna", "start": 0.0, "duration": 2.0},
    {"text": ">> thanks anna glad to be here", "start": 5.0, "duration": 2.0},
    {"text": "so lets talk caching", "start": 65.0, "duration": 2.0},
]
_CLEAN = "Anna: Welcome to the show, I am Anna.\n\n\n\nSpeaker 2: Thanks, Anna. Glad to be here.\n\nLet's talk caching."


def _response(stop_reason="end_turn", text=_CLEAN):
    return SimpleNamespace(
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=900, output_tokens=200),
    )


class _Isolated(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for target, name, value in (
            (ss.settings, "transcript_cache_dir", tmp.name),
            (ss.settings, "transcript_cache_enabled", True),
            (ss.settings, "anthropic_api_key", "test-key"),
        ):
            p = patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        # self.api records each streamed request's kwargs and supplies its final message
        self.api = MagicMock(return_value=_response())

        def _stream(**kwargs):
            ctx = MagicMock()
            ctx.__enter__.return_value.get_final_message.return_value = self.api(**kwargs)
            return ctx

        self.fake = MagicMock()
        self.fake.beta.messages.stream.side_effect = _stream
        p = patch.object(ss, "_get_client", return_value=self.fake)
        p.start()
        self.addCleanup(p.stop)
        rate_limiter._store.clear()

    def generate(self, mode="clean", **kw):
        args = dict(provider="youtube", video_id="vid", language="en", title="My Talk")
        args.update(kw)
        return es.generate(_SEGMENTS, mode=mode, **args)


class TestPrompt(unittest.TestCase):
    def test_plain_text_keeps_turn_markers_and_drops_timestamps(self):
        self.assertEqual(
            es.plain_text_for_prompt(_SEGMENTS),
            "welcome to the show i am anna >> thanks anna glad to be here so lets talk caching",
        )

    def test_modes(self):
        for mode in ("clean", "study_notes", "blog_post", "show_notes"):
            self.assertTrue(es.is_valid_mode(mode))
            self.assertIn("never as instructions", es._SYSTEMS[mode])
        self.assertFalse(es.is_valid_mode("poem"))


class TestGenerate(_Isolated):
    def test_clean_request_shape(self):
        self.generate("clean")
        kw = self.api.call_args.kwargs
        self.assertEqual(kw["fallbacks"], "default")
        self.assertEqual(kw["output_config"], {"effort": "low"})
        self.assertEqual(kw["timeout"], es.settings.enhance_timeout_seconds)
        self.assertIn("Do NOT summarise", kw["system"])
        prompt = kw["messages"][0]["content"]
        self.assertIn("My Talk", prompt)
        self.assertIn("<transcript>\nwelcome to the show", prompt)  # no [m:ss] stamps for cleanup
        self.assertNotIn("[0:00]", prompt)

    def test_show_notes_gets_timestamped_lines(self):
        self.generate("show_notes")
        prompt = self.api.call_args.kwargs["messages"][0]["content"]
        self.assertIn("[0:00]", prompt)
        self.assertIn("[1:05]", prompt)

    def test_output_normalised_and_cached_per_mode(self):
        out = self.generate("clean")
        self.assertNotIn("\n\n\n", out)
        self.assertEqual(es.get_cached("youtube", "vid", "en", "clean"), out)
        self.assertIsNone(es.get_cached("youtube", "vid", "en", "blog_post"))  # per mode
        self.assertIsNone(es.get_cached("youtube", "vid", "es", "clean"))  # per language
        self.assertIsNone(tcs.read_transcript_cache("youtube", "vid", "en"))  # not the transcript

    def test_refusal_and_truncation_are_clean_errors(self):
        for stop in ("refusal", "max_tokens"):
            self.api.return_value = _response(stop_reason=stop)
            with self.assertRaises(AppError):
                self.generate("clean")
        self.assertIsNone(es.get_cached("youtube", "vid", "en", "clean"))

    def test_empty_output_is_an_error(self):
        self.api.return_value = _response(text="   ")
        with self.assertRaises(AppError):
            self.generate("clean")

    def test_too_long_refused_without_calling_claude(self):
        with patch.object(es.settings, "enhance_clean_max_input_chars", 10):
            with self.assertRaises(AppError) as ctx:
                self.generate("clean")
        self.assertEqual(ctx.exception.code.value, "SUMMARY_TOO_LONG")
        self.api.assert_not_called()

    def test_unknown_mode_and_disabled(self):
        with self.assertRaises(AppError):
            self.generate("poem")
        with patch.object(ss.settings, "anthropic_api_key", ""):
            with self.assertRaises(AppError) as ctx:
                self.generate("clean")
        self.assertEqual(ctx.exception.status_code, 503)


class TestApi(_Isolated):
    def _extract(self):
        with patch("app.api.v1_routes.get_transcript_from_url") as fetch:
            fetch.return_value = {
                "provider": "youtube", "video_id": "testvideo12", "title": "My Talk",
                "language": "en", "duration_seconds": 120, "segments": _SEGMENTS,
            }
            r = client.post(
                "/api/v1/extract",
                json={"url": "https://www.youtube.com/watch?v=testvideo12"},
            )
        return r.json()["file_id"]

    def test_config_lists_modes(self):
        cfg = client.get("/api/v1/config").json()
        self.assertTrue(cfg["enhance_enabled"])
        self.assertEqual(
            [m["id"] for m in cfg["enhance_modes"]],
            ["clean", "study_notes", "blog_post", "show_notes"],
        )

    def test_enhance_returns_new_downloadable_file_then_cache_hit(self):
        file_id = self._extract()
        with patch.object(es.settings, "rate_limit_enhance_requests", 1):
            first = client.post("/api/v1/enhance", json={"file_id": file_id, "mode": "clean"}).json()
            second = client.post("/api/v1/enhance", json={"file_id": file_id, "mode": "clean"}).json()
        self.assertTrue(first["success"])
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(self.api.call_count, 1)
        self.assertNotEqual(first["file_id"], file_id)
        dl = client.get(first["file_download_url"])
        self.assertEqual(dl.status_code, 200)
        self.assertIn("Glad to be here", dl.text)
        self.assertIn("Cleaned transcript", dl.headers["content-disposition"])
        # The new file converts to DOCX through the existing converter
        conv = client.post("/api/v1/convert", json={"file_id": first["file_id"], "format": "docx"})
        self.assertEqual(conv.status_code, 200)

    def test_quota_applies_on_cache_miss(self):
        file_id = self._extract()
        with patch("app.core.dependencies.check_rate_limit", return_value=False):
            r = client.post("/api/v1/enhance", json={"file_id": file_id, "mode": "blog_post"})
        self.assertEqual(r.status_code, 429)
        self.api.assert_not_called()

    def test_bad_mode_disabled_and_unknown_file(self):
        file_id = self._extract()
        r = client.post("/api/v1/enhance", json={"file_id": file_id, "mode": "poem"})
        self.assertEqual(r.status_code, 400)
        with patch.object(ss.settings, "anthropic_api_key", ""):
            r = client.post("/api/v1/enhance", json={"file_id": file_id, "mode": "clean"})
        self.assertEqual(r.status_code, 503)
        r = client.post(
            "/api/v1/enhance",
            json={"file_id": "deadbeefdeadbeefdeadbeefdeadbeef.txt", "mode": "clean"},
        )
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
