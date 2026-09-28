"""Language picker: matching rules, target-language fetch, cache keys, API, PDF fonts."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.languages import LANGUAGE_CODES, language_name, languages_match
from app.main import app
from app.services.rate_limit_service import rate_limiter
from app.services import pdf_fonts
from app.services import transcript_cache_service as tcs
from app.services import transcript_service as ts
from app.services.file_service import FileGenerator

client = TestClient(app)


class TestLanguageMatching(unittest.TestCase):
    def test_regional_variants_match(self):
        self.assertTrue(languages_match("en-GB", "en"))
        self.assertTrue(languages_match("pt-BR", "pt"))
        self.assertFalse(languages_match("es", "en"))

    def test_chinese_scripts_do_not_match(self):
        self.assertTrue(languages_match("zh-TW", "zh-Hant"))
        self.assertTrue(languages_match("zh-CN", "zh-Hans"))
        self.assertFalse(languages_match("zh-Hans", "zh-Hant"))

    def test_language_name_handles_variants(self):
        self.assertEqual(language_name("en-GB"), "English")
        self.assertEqual(language_name("zh-TW"), "繁體中文")
        self.assertEqual(language_name("fil"), "fil")


class _Fetched(list):
    def __init__(self, code, items):
        super().__init__(items)
        self.language_code = code


def _track(code, translations=()):
    tr = MagicMock(language_code=code, is_translatable=bool(translations))
    tr.translation_languages = [SimpleNamespace(language_code=c) for c in translations]
    tr.fetch.return_value = _Fetched(code, [SimpleNamespace(text=f"{code} text", start=0.0, duration=1.0)])
    tr.translate.side_effect = lambda c: MagicMock(
        fetch=MagicMock(return_value=_Fetched(c, [SimpleNamespace(text=f"{c} text", start=0.0, duration=1.0)]))
    )
    return tr


def _fetch_with_tracks(tracks, target):
    """Run the YouTube core against a fake caption list."""
    by_code = {t.language_code: t for t in tracks}
    tlist = MagicMock(video_id="vid")

    def find(codes):
        for c in codes:
            if c in by_code:
                return by_code[c]
        raise ts.NoTranscriptFound("vid", list(codes), tlist)

    tlist.find_transcript.side_effect = find
    tlist.__iter__.side_effect = lambda: iter(tracks)
    api = MagicMock()
    api.list.return_value = tlist
    with patch.object(ts, "YouTubeTranscriptApi", return_value=api), patch.object(
        ts, "_get_youtube_metadata", return_value={"title": "T", "duration": 0}
    ):
        return ts.get_youtube_transcript("vid", target_language=target)


class TestTargetLanguageFetch(unittest.TestCase):
    def test_native_track_preferred(self):
        out = _fetch_with_tracks([_track("en", ["es"]), _track("es")], "es")
        self.assertEqual(out["language"], "es")
        self.assertFalse(out["translated"])

    def test_translates_when_no_native_track(self):
        out = _fetch_with_tracks([_track("en", ["es", "ja"])], "ja")
        self.assertEqual(out["language"], "ja")
        self.assertEqual(out["source_language"], "en")
        self.assertTrue(out["translated"])

    def test_traditional_chinese_not_served_simplified(self):
        out = _fetch_with_tracks([_track("zh-Hans", ["zh-Hans", "zh-Hant"])], "zh-Hant")
        self.assertEqual(out["language"], "zh-Hant")
        self.assertTrue(out["translated"])

    def test_blocked_translation_is_an_error_not_a_fallback(self):
        source = _track("en", ["ja"])
        source.translate.side_effect = None
        source.translate.return_value.fetch.side_effect = ts.IpBlocked("vid")
        with patch.object(ts, "write_transcript_cache") as write_cache:
            with self.assertRaises(ts.TranscriptFetchError) as ctx:
                _fetch_with_tracks([source], "ja")
        self.assertEqual(ctx.exception.code.value, "UPSTREAM_BLOCKED")
        write_cache.assert_not_called()

    def test_falls_back_to_original_when_untranslatable(self):
        out = _fetch_with_tracks([_track("de")], "fr")
        self.assertEqual(out["language"], "de")
        self.assertFalse(out["translated"])


class TestCacheKey(unittest.TestCase):
    def test_language_in_cache_path(self):
        self.assertNotEqual(
            tcs.cache_path("youtube", "vid", "en"), tcs.cache_path("youtube", "vid", "es")
        )


class TestApi(unittest.TestCase):

    def setUp(self):
        # All TestClient requests share one "IP"; other suites' extracts must not exhaust its quota
        rate_limiter._store.clear()
    def _extract(self, mock_fetch, data, language="es"):
        mock_fetch.return_value = data
        return client.post(
            "/api/v1/extract",
            json={
                "url": "https://www.youtube.com/watch?v=testvideo12",
                "include_timestamps": False,
                "language": language,
            },
        )

    def test_config_lists_languages(self):
        body = client.get("/api/v1/config").json()
        self.assertEqual(body["default_language"], "en")
        self.assertEqual({l["code"] for l in body["languages"]}, set(LANGUAGE_CODES))

    def test_unknown_language_rejected(self):
        r = client.post(
            "/api/v1/extract",
            json={"url": "https://www.youtube.com/watch?v=testvideo12", "language": "xx"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["code"], "UNSUPPORTED_LANGUAGE")

    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_translated_response(self, mock_fetch):
        r = self._extract(mock_fetch, {
            "provider": "youtube", "video_id": "testvideo12", "title": "T",
            "language": "es", "source_language": "en", "translated": True,
            "duration_seconds": 5, "segments": [{"text": "Hola", "start": 0, "duration": 1}],
        })
        body = r.json()
        self.assertEqual(mock_fetch.call_args.args[2], "es")
        self.assertEqual(body["language_name"], "Español")
        self.assertEqual(body["source_language_name"], "English")
        self.assertTrue(body["translated"])
        self.assertFalse(body["language_fallback"])
        self.assertTrue(body["pdf_supported"])

    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_arabic_fallback_disables_pdf(self, mock_fetch):
        r = self._extract(mock_fetch, {
            "provider": "youtube", "video_id": "testvideo12", "title": "T",
            "language": "ar", "source_language": "ar", "translated": False,
            "duration_seconds": 5, "segments": [{"text": "مرحبا بالعالم", "start": 0, "duration": 1}],
        })
        body = r.json()
        self.assertTrue(body["language_fallback"])
        self.assertFalse(body["pdf_supported"])

        conv = client.post("/api/v1/convert", json={"file_id": body["file_id"], "format": "pdf"})
        self.assertEqual(conv.status_code, 400)
        self.assertIn("PDF isn't available", conv.json()["error"]["message"])
        docx = client.post("/api/v1/convert", json={"file_id": body["file_id"], "format": "docx"})
        self.assertEqual(docx.status_code, 200)


class TestPdfFonts(unittest.TestCase):
    def test_western_stays_helvetica(self):
        self.assertEqual(pdf_fonts.pdf_font_for("Café déjà vu").name, "Helvetica")

    def test_cjk_uses_cid_font_with_cjk_wrap(self):
        font = pdf_fonts.pdf_font_for("你好世界", "zh-Hant")
        self.assertEqual(font.name, "MSung-Light")
        self.assertTrue(font.cjk_wrap)
        self.assertEqual(pdf_fonts.pdf_font_for("こんにちは").name, "HeiseiKakuGo-W5")

    def test_complex_scripts_refused(self):
        for text in ("مرحبا", "नमस्ते", "שלום", "สวัสดี"):
            with self.assertRaises(pdf_fonts.UnsupportedPdfScript):
                pdf_fonts.pdf_font_for(text)

    def test_symbols_never_block_a_western_pdf(self):
        with patch.object(pdf_fonts, "_register_ttf", return_value=None):
            font = pdf_fonts.pdf_font_for("[♪ music ♪] hello 🎉")
        self.assertEqual(font.name, "Helvetica")
        self.assertEqual(font.drop, frozenset({"♪", "🎉"}))

    def test_letters_without_font_refused(self):
        with patch.object(pdf_fonts, "_register_ttf", return_value=None):
            with self.assertRaises(pdf_fonts.UnsupportedPdfScript):
                pdf_fonts.pdf_font_for("Привет")

    def test_letters_missing_from_font_refused(self):
        with patch.object(pdf_fonts, "_register_ttf", return_value={ord("П")}):
            with self.assertRaises(pdf_fonts.UnsupportedPdfScript):
                pdf_fonts.pdf_font_for("Привет")

    @unittest.skipUnless(pdf_fonts._register_ttf("TranscriptUnicode", pdf_fonts._TTF_CANDIDATES), "no Unicode TTF on this machine")
    def test_cyrillic_pdf_builds_with_embedded_font(self):
        path = FileGenerator.generate_pdf("Привет, как дела")
        with open(path, "rb") as f:
            self.assertIn(b"/FontFile2", f.read())  # embedded TrueType, not Helvetica


if __name__ == "__main__":
    unittest.main()
