"""Rate limit buckets must not share extract quota with events/download."""

import unittest
from unittest.mock import patch

from app.services.rate_limit_service import RateLimitService


class TestRateLimitBuckets(unittest.TestCase):
    def test_extract_and_events_are_independent(self):
        svc = RateLimitService()
        with patch("app.services.rate_limit_service.settings") as s:
            s.rate_limit_requests = 2
            s.rate_limit_convert_requests = 40
            s.rate_limit_events_requests = 100
            s.rate_limit_download_requests = 200
            s.rate_limit_window_seconds = 86400

            self.assertTrue(svc.is_allowed("1.1.1.1", bucket="extract"))
            self.assertTrue(svc.is_allowed("1.1.1.1", bucket="extract"))
            self.assertFalse(svc.is_allowed("1.1.1.1", bucket="extract"))
            # Events still allowed after extract exhausted
            self.assertTrue(svc.is_allowed("1.1.1.1", bucket="events"))

    def test_zero_limit_is_unlimited(self):
        svc = RateLimitService()
        with patch("app.services.rate_limit_service.settings") as s:
            s.rate_limit_requests = 10
            s.rate_limit_convert_requests = 0
            s.rate_limit_events_requests = 0
            s.rate_limit_download_requests = 0
            s.rate_limit_window_seconds = 86400
            for _ in range(50):
                self.assertTrue(svc.is_allowed("ip", bucket="events"))


if __name__ == "__main__":
    unittest.main()
