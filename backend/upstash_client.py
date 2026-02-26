from __future__ import annotations

import json
import urllib.request
from typing import Any


class UpstashError(RuntimeError):
    pass


class Redis:
    """Minimal Upstash REST client for rate limiting and lightweight counters."""

    def __init__(self, url: str, token: str) -> None:
        if not url or not token:
            raise ValueError("Upstash url and token are required")
        self.url = url.rstrip("/")
        self.token = token

    def _post(self, body: dict[str, Any]) -> Any:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as resp:  # type: ignore[arg-type]
            payload = json.loads(resp.read().decode("utf-8"))
            if "error" in payload:
                raise UpstashError(payload["error"])
            return payload.get("result")

    def incr(self, key: str) -> int:
        result = self._post({"command": ["INCR", key]})
        return int(result)

    def expire(self, key: str, seconds: int) -> None:
        self._post({"command": ["EXPIRE", key, seconds]})

