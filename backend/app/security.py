import hmac
import hashlib


def verify_signature(raw_body: bytes, api_key: str, signature: str | None) -> bool:
    """Retell signs each webhook body with HMAC-SHA256 keyed on your API key."""
    if not api_key or not signature:
        return False
    expected = hmac.new(api_key.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
