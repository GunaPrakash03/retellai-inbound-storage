import hmac
import hashlib
import re
import time
from collections import defaultdict, deque

# Matches Retell's "v={timestamp_ms},d={hex_digest}" signature header format.
_SIGNATURE_RE = re.compile(r"v=(\d+),d=(.*)")

MAX_SIGNATURE_AGE_MS = 5 * 60 * 1000  # reject signatures older than 5 minutes


def verify_signature(raw_body: bytes, api_key: str, signature: str | None) -> bool:
    """Verifies Retell's `x-retell-signature` header.

    Retell signs `raw_body + timestamp` with HMAC-SHA256 keyed on your API
    key, and sends it as `v={timestamp_ms},d={hex_digest}`.
    """
    if not api_key or not signature:
        return False

    match = _SIGNATURE_RE.match(signature)
    if not match:
        return False

    timestamp, digest = match.group(1), match.group(2)

    age_ms = int(time.time() * 1000) - int(timestamp)
    if age_ms > MAX_SIGNATURE_AGE_MS or age_ms < -MAX_SIGNATURE_AGE_MS:
        return False

    expected = hmac.new(
        api_key.encode(),
        raw_body + timestamp.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, digest)


class SlidingWindowLimiter:
    """Counts events per key over a rolling window.

    In-memory on purpose: the Procfile runs a single uvicorn worker, so one
    process sees all traffic. If the deployment ever grows extra workers,
    move the counters into the DB or the limits stop being global.
    """

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque:
        q = self._hits[key]
        cutoff = now - self.window
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def blocked(self, key: str, now: float | None = None) -> bool:
        """True if `key` is at its limit. Does not record anything."""
        now = time.time() if now is None else now
        return len(self._prune(key, now)) >= self.limit

    def record(self, key: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._prune(key, now).append(now)
        # Keep the key map from growing without bound under IP churn. Prune
        # every key before judging it: a key touched once and never queried
        # again still holds its stale timestamp, and skipping the prune here
        # would mean such keys are never freed.
        if len(self._hits) > 10_000:
            for k in list(self._hits):
                if not self._prune(k, now):
                    del self._hits[k]

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record-and-check in one step: False once `key` is over its limit."""
        now = time.time() if now is None else now
        if self.blocked(key, now):
            return False
        self.record(key, now)
        return True
