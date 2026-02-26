from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from upstash_client import Redis


class RateLimiter:
    def __init__(self, max_calls: int = 8, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.redis = None

        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if redis_url and redis_token:
            try:
                self.redis = Redis(url=redis_url, token=redis_token)
            except Exception as exc:
                print(f"[WARN] Failed to connect to Upstash Redis: {exc}")

        self.local_calls: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        if self.redis:
            try:
                redis_key = f"ratelimit:{key}"
                res = self.redis.incr(redis_key)
                if res == 1:
                    self.redis.expire(redis_key, self.window_seconds)
                return res <= self.max_calls
            except Exception as exc:
                print(f"[WARN] Redis rate limit error: {exc}")
                # fall back to local window

        now = time.time()
        queue = self.local_calls[key]
        cutoff = now - self.window_seconds

        while queue and queue[0] < cutoff:
            queue.popleft()

        if len(queue) >= self.max_calls:
            return False

        queue.append(now)
        return True
