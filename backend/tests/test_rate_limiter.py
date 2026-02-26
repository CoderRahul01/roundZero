import unittest
from unittest.mock import MagicMock, patch

from rate_limit import RateLimiter


class RateLimiterTests(unittest.TestCase):
    def test_allows_within_limit_local(self):
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        self.assertTrue(limiter.allow("u1"))
        self.assertTrue(limiter.allow("u1"))
        self.assertFalse(limiter.allow("u1"))

    def test_redis_path_uses_expire(self):
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = [1, 2, 3]
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        limiter.redis = mock_redis

        self.assertTrue(limiter.allow("k"))
        mock_redis.expire.assert_called_with("ratelimit:k", 60)
        self.assertTrue(limiter.allow("k"))
        self.assertFalse(limiter.allow("k"))

    @patch("rate_limit.Redis", side_effect=Exception("fail"))
    def test_graceful_when_redis_init_fails(self, _):
        limiter = RateLimiter(max_calls=1, window_seconds=60)
        self.assertTrue(limiter.allow("k"))


if __name__ == "__main__":
    unittest.main()
