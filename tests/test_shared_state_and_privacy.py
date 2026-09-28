"""Redis-shared rate limits / bot prefs (with in-memory fallback) and log privacy."""

import hashlib
import json
import os
import unittest
from unittest.mock import patch

import redis

from app.services import rate_limit_service as rls
from app.services import telemetry_service
from app.services import user_prefs_service as prefs
from app.services.metadata_service import MetadataService


class _FakePipeline:
    def __init__(self, store):
        self._store = store
        self._ops = []

    def __getattr__(self, name):
        def queue(*args, **kwargs):
            self._ops.append((name, args, kwargs))
            return self
        return queue

    def execute(self):
        return [getattr(self._store, name)(*a, **kw) for name, a, kw in self._ops]


class FakeRedis:
    """Just the commands the app uses; TTLs recorded, not enforced."""

    def __init__(self):
        self.data = {}
        self.ttl = {}

    def pipeline(self, transaction=True):
        return _FakePipeline(self)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return None
        self.data[key] = str(value)
        self.ttl[key] = ex
        return True

    def incr(self, key):
        self.data[key] = str(int(self.data.get(key, 0)) + 1)
        return int(self.data[key])

    def hgetall(self, key):
        return dict(self.data.get(key, {}))

    def hset(self, key, mapping):
        self.data.setdefault(key, {}).update(mapping)
        return len(mapping)

    def expire(self, key, seconds):
        self.ttl[key] = seconds
        return True


class _BrokenRedis:
    def pipeline(self, transaction=True):
        raise redis.ConnectionError("down")

    def hgetall(self, key):
        raise redis.ConnectionError("down")


def _limits(s, extract=2):
    s.rate_limit_requests = extract
    s.rate_limit_convert_requests = 40
    s.rate_limit_events_requests = 100
    s.rate_limit_download_requests = 200
    s.rate_limit_window_seconds = 3600


class TestSharedRateLimit(unittest.TestCase):
    def test_count_is_shared_between_limiter_instances(self):
        fake = FakeRedis()
        worker_a, worker_b = rls.RateLimitService(), rls.RateLimitService()
        with patch.object(rls, "get_redis", return_value=fake), patch.object(rls, "settings") as s:
            _limits(s)
            self.assertTrue(worker_a.is_allowed("1.1.1.1"))
            self.assertTrue(worker_b.is_allowed("1.1.1.1"))
            # Third request is blocked no matter which worker receives it
            self.assertFalse(worker_a.is_allowed("1.1.1.1"))
            self.assertTrue(worker_b.is_allowed("1.1.1.1", bucket="events"))
        self.assertEqual(fake.ttl["tf:rl:extract:1.1.1.1"], 3600)

    def test_falls_back_to_memory_when_redis_down(self):
        svc = rls.RateLimitService()
        with patch.object(rls, "get_redis", return_value=_BrokenRedis()), patch.object(
            rls, "settings"
        ) as s, patch.object(rls, "warn_fallback") as warn:
            _limits(s)
            self.assertTrue(svc.is_allowed("ip"))
            self.assertTrue(svc.is_allowed("ip"))
            self.assertFalse(svc.is_allowed("ip"))
        warn.assert_called()


@unittest.skipUnless(os.environ.get("TEST_REDIS_URL"), "TEST_REDIS_URL not set (CI provides one)")
class TestRealRedis(unittest.TestCase):
    """Same behaviour against a real server (MULTI/SET NX EX/INCR, hash + TTL)."""

    def setUp(self):
        self.client = redis.Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        self.client.flushdb()
        self.addCleanup(self.client.flushdb)

    def test_rate_limit_shared_with_ttl(self):
        with patch.object(rls, "get_redis", return_value=self.client), patch.object(
            rls, "settings"
        ) as s:
            _limits(s)
            results = [rls.RateLimitService().is_allowed("ip") for _ in range(3)]
        self.assertEqual(results, [True, True, False])
        self.assertTrue(0 < self.client.ttl("tf:rl:extract:ip") <= 3600)

    def test_prefs_roundtrip(self):
        prefs._memory.clear()
        with patch.object(prefs, "get_redis", return_value=self.client):
            prefs.set_prefs("42", last_file_format="vtt", last_include_timestamps=True)
            prefs._memory.clear()
            self.assertEqual(prefs.get_prefs("42")["last_file_format"], "vtt")
        self.assertGreater(self.client.ttl("tf:tgprefs:42"), 86400)


class TestTelegramPrefs(unittest.TestCase):
    def setUp(self):
        prefs._memory.clear()

    def test_defaults(self):
        with patch.object(prefs, "get_redis", return_value=None):
            self.assertEqual(prefs.get_prefs("42"), prefs.DEFAULTS)

    def test_roundtrip_through_redis_survives_process_memory_loss(self):
        fake = FakeRedis()
        with patch.object(prefs, "get_redis", return_value=fake):
            prefs.set_prefs(
                "42", last_file_format="srt", last_include_timestamps=True, language="ja"
            )
            prefs._memory.clear()  # simulate a restart
            self.assertEqual(
                prefs.get_prefs("42"),
                {"last_file_format": "srt", "last_include_timestamps": True, "language": "ja"},
            )
        self.assertEqual(fake.ttl["tf:tgprefs:42"], prefs.settings.telegram_prefs_ttl_days * 86400)

    def test_invalid_stored_values_ignored(self):
        fake = FakeRedis()
        fake.data["tf:tgprefs:7"] = {
            "last_file_format": "exe",
            "last_include_timestamps": "yes",
            "language": "klingon",
        }
        with patch.object(prefs, "get_redis", return_value=fake):
            self.assertEqual(prefs.get_prefs("7"), prefs.DEFAULTS)

    def test_memory_fallback_when_redis_down(self):
        with patch.object(prefs, "get_redis", return_value=_BrokenRedis()), patch.object(
            prefs, "warn_fallback"
        ):
            prefs.set_prefs("9", last_file_format="pdf")
            self.assertEqual(prefs.get_prefs("9")["last_file_format"], "pdf")

    def test_unknown_pref_rejected(self):
        with self.assertRaises(ValueError):
            prefs.set_prefs("1", theme="dark")


class TestLogPrivacy(unittest.TestCase):
    def test_hash_is_keyed_not_plain_sha256(self):
        ip = "203.0.113.7"
        hashed = telemetry_service.hash_identifier(ip)
        self.assertEqual(hashed, telemetry_service.hash_identifier(ip))
        self.assertNotEqual(hashed, hashlib.sha256(ip.encode()).hexdigest()[:16])

    def _logged_json(self, mock_logger_method):
        return json.loads(mock_logger_method.call_args.args[0])

    @patch("app.services.metadata_service.logger")
    def test_failure_log_has_video_id_not_url(self, mock_logger):
        MetadataService.log_failure(
            url="https://youtu.be/dQw4w9WgXcQ?si=SHARETOKEN",
            platform="youtube",
            error_code="TRANSCRIPT_NOT_AVAILABLE",
            error_message="x",
            processing_time_ms=1,
        )
        data = self._logged_json(mock_logger.error)
        self.assertEqual(data["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(data["host"], "youtu.be")
        self.assertNotIn("url", data)
        self.assertNotIn("SHARETOKEN", json.dumps(data))

    @patch("app.services.metadata_service.logger")
    def test_rate_limit_block_log_hashes_ip(self, mock_logger):
        from fastapi.testclient import TestClient
        from app.main import app

        with patch("app.core.dependencies.check_rate_limit", return_value=False):
            r = TestClient(app).post("/api/v1/events", json={})
        self.assertEqual(r.status_code, 429)
        logged = mock_logger.warning.call_args.args[0]
        self.assertNotIn("testclient", logged)  # TestClient's socket "IP"
        self.assertIn(telemetry_service.hash_identifier("testclient"), logged)


if __name__ == "__main__":
    unittest.main()
