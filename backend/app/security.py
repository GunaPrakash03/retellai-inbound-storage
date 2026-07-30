import hmac
import hashlib
import re
import time

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
