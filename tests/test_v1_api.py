"""Contract tests for /api/v1 extract and convert (mocked upstream transcript)."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_TRANSCRIPT = {
    "provider": "youtube",
    "source_url": "https://www.youtube.com/watch?v=testvideo12",
    "video_id": "testvideo12",
    "title": "Unit Test Video",
    "language": "en",
    "duration_seconds": 120,
    "segments": [
        {"text": "Hello", "start": 0.0, "duration": 0.5},
        {"text": "world", "start": 0.5, "duration": 0.5},
    ],
}


class TestV1Extract(unittest.TestCase):
    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_extract_success_envelope(self, mock_fetch):
        mock_fetch.return_value = {**_TRANSCRIPT}
        r = client.post(
            "/api/v1/extract",
            json={
                "url": "https://www.youtube.com/watch?v=testvideo12",
                "include_timestamps": False,
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["title"], "Unit Test Video")
        self.assertEqual(data["video_id"], "testvideo12")
        self.assertIn("file_id", data)
        self.assertTrue(data["file_id"].endswith(".txt"))
        self.assertTrue(data["file_download_url"].startswith("/api/v1/download/"))
        self.assertIn("preview_text", data)
        self.assertIn("reading_time_seconds", data)
        self.assertIn("expires_at", data)

    def test_extract_invalid_url(self):
        r = client.post(
            "/api/v1/extract",
            json={"url": "https://example.com/not-a-video", "include_timestamps": False},
        )
        self.assertEqual(r.status_code, 400)
        body = r.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "INVALID_URL")

    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_extract_transcript_not_available(self, mock_fetch):
        mock_fetch.side_effect = Exception("Transcripts are disabled for this video.")
        r = client.post(
            "/api/v1/extract",
            json={
                "url": "https://www.youtube.com/watch?v=testvideo12",
                "include_timestamps": False,
            },
        )
        self.assertEqual(r.status_code, 400)
        body = r.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "TRANSCRIPT_NOT_AVAILABLE")

    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_extract_internal_error_hides_exception_detail(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("DB password=secret and internal stack …")
        r = client.post(
            "/api/v1/extract",
            json={
                "url": "https://www.youtube.com/watch?v=testvideo12",
                "include_timestamps": False,
            },
        )
        self.assertEqual(r.status_code, 500)
        body = r.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("password", body["error"]["message"])
        self.assertEqual(body["error"]["message"], "An unexpected error occurred.")


class TestV1Convert(unittest.TestCase):
    @patch("app.api.v1_routes.get_transcript_from_url")
    def test_convert_txt_returns_download_url(self, mock_fetch):
        mock_fetch.return_value = {**_TRANSCRIPT}
        ex = client.post(
            "/api/v1/extract",
            json={
                "url": "https://www.youtube.com/watch?v=testvideo12",
                "include_timestamps": False,
            },
        )
        self.assertEqual(ex.status_code, 200)
        file_id = ex.json()["file_id"]

        conv = client.post(
            "/api/v1/convert",
            json={"file_id": file_id, "format": "txt"},
        )
        self.assertEqual(conv.status_code, 200)
        c = conv.json()
        self.assertTrue(c["success"])
        self.assertIn("file_download_url", c)
        self.assertTrue(c["file_download_url"].startswith("/api/v1/download/"))

    def test_convert_rejects_bad_format(self):
        r = client.post(
            "/api/v1/convert",
            json={"file_id": "deadbeefdeadbeefdeadbeefdeadbeef.txt", "format": "zip"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["success"])

    def test_download_rejects_raw_sidecar_extension(self):
        r = client.get(
            "/api/v1/download/deadbeefdeadbeefdeadbeefdeadbeef.raw",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["success"])


class TestV1Health(unittest.TestCase):
    def test_health(self):
        r = client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "ok")


if __name__ == "__main__":
    unittest.main()
