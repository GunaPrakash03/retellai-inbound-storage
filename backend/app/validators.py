import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

VALID_CATEGORIES = {
    "personal_injury",
    "workplace_employment",
    "medical_product",
    "family_law",
    "criminal_defense",
    "immigration",
    "real_estate_housing",
    "business_contract",
    "estate_disability",
    "other",
}


def normalize_category(category: str | None) -> str | None:
    """Retell's Selector extraction occasionally tacks on stray punctuation
    (e.g. "personal_injury,") which then fails to match the fixed category
    list used for display. Strip it back down to the clean value."""
    if not category:
        return category
    cleaned = category.strip().strip(",.;: ").lower()
    return cleaned if cleaned in VALID_CATEGORIES else cleaned or category


def is_valid_phone(phone: str | None) -> bool | None:
    """The callback number itself must be exactly 10 digits, with an
    optional 1-3 digit country code in front (matches the agent prompt's
    phone number rules). Returns None (unknown) if no phone was captured at
    all, rather than False, so an empty field isn't shown as "invalid"."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    extra = len(digits) - 10
    return 0 <= extra <= 3


def is_valid_email(email: str | None) -> bool | None:
    if not email:
        return None
    return bool(_EMAIL_RE.match(email.strip()))


# Exact (lowercased) fragments lifted from the agent prompt's own scripted
# endings. Retell's call_outcome Post-Call Data Extraction field has been
# observed to mislabel calls as "completed" even when the transcript
# contains one of these verbatim — searching the transcript ourselves for
# text we control is deterministic where an LLM classification isn't.
_OUTCOME_PHRASES = [
    ("emergency", "hang up and call 911 right now"),
    ("emergency", "your safety comes first"),
    ("unwanted", "having a hard time following the details"),
    ("spam", "might not be the right time to go through these details"),
    ("partial", "we may have gotten disconnected"),
    ("completed", "i have everything i need"),
]


def detect_outcome_from_transcript(transcript: str | None) -> str | None:
    """Returns one of "emergency"/"unwanted"/"spam"/"partial"/"completed" by
    matching the agent's own scripted closing lines in the transcript, or
    None if no scripted ending is present (e.g. the call dropped for a
    reason outside the agent's control)."""
    if not transcript:
        return None
    lowered = transcript.lower()
    for outcome, phrase in _OUTCOME_PHRASES:
        if phrase in lowered:
            return outcome
    return None
