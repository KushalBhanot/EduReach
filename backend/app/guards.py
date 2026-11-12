"""Per-instance rate limiting and idempotency.

Both are in memory, so they hold per Cloud Run instance. With
max-instances=2 that is good enough to stop casual abuse of an
unauthenticated endpoint; it is not authentication.
"""

import time
from collections import OrderedDict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_s: float = 60.0):
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] > self.window_s:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        if len(self._hits) > 10_000:  # drop idle keys so memory stays bounded
            self._hits = {k: v for k, v in self._hits.items() if v}
        return True


class IdempotencyCache:
    def __init__(self, ttl_s: float = 600.0, max_items: int = 1000):
        self.ttl_s = ttl_s
        self.max_items = max_items
        self._items: OrderedDict[str, tuple[float, object]] = OrderedDict()

    def get(self, key: str):
        item = self._items.get(key)
        if item is None:
            return None
        stored_at, value = item
        if time.monotonic() - stored_at > self.ttl_s:
            del self._items[key]
            return None
        return value

    def put(self, key: str, value: object) -> None:
        self._items[key] = (time.monotonic(), value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)
