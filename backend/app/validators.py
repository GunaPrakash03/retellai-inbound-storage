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
    """A US callback number: exactly 10 digits, optionally with a leading
    country code 1. Returns None (unknown) if no phone was captured at all,
    rather than False, so an empty field isn't shown as "invalid"."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return len(digits) == 10


def is_valid_email(email: str | None) -> bool | None:
    if not email:
        return None
    return bool(_EMAIL_RE.match(email.strip()))
