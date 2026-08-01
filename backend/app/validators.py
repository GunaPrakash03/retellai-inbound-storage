import re
from difflib import SequenceMatcher

from .taxonomy import (
    EMPLOYMENT_CATEGORY,
    EMPLOYMENT_SUBTYPES,
    EMPLOYMENT_TYPE_LABELS,
    slugify as _clean_slug,
)

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


# Finer-grained matter types within each category. Keyed by category, and
# kept in step with the matter types the agent prompt's Step 1 / Step 3
# already ask about — the extraction can only reliably pick values the
# agent actually asked the questions to distinguish. "other" has no list:
# by definition it holds what didn't fit a taxonomy.
VALID_SUBCATEGORIES = {
    "personal_injury": {
        "car_accident",
        "motorcycle_accident",
        "truck_accident",
        "pedestrian_bicycle_accident",
        "slip_and_fall",
        "dog_bite",
        "wrongful_death",
        "boating_accident",
    },
    # Employment's case types come from the full taxonomy (25 of them); its
    # third level (subtype) lives in VALID_SUBTYPES below. See taxonomy.py.
    "workplace_employment": set(EMPLOYMENT_TYPE_LABELS),
    "medical_product": {
        "medical_malpractice",
        "defective_product",
        "dangerous_drug_device",
    },
    "family_law": {
        "divorce",
        "child_custody_visitation",
        "child_support",
        "paternity",
        "adoption_guardianship",
        "domestic_violence_protection",
        "emancipation_name_changes",
    },
    "criminal_defense": {
        "dui_dwi",
        "misdemeanor",
        "felony",
        "traffic_violation",
        "juvenile",
    },
    "immigration": {
        "visa",
        "green_card",
        "deportation_removal",
        "asylum",
        "citizenship_naturalization",
    },
    "real_estate_housing": {
        "landlord_tenant",
        "eviction",
        "purchase_sale_dispute",
        "foreclosure",
    },
    "business_contract": {
        "breach_of_contract",
        "partnership_dispute",
        "debt_collection",
    },
    "estate_disability": {
        "estate_planning",
        "probate",
        "social_security_disability",
        "veterans_benefits",
    },
}


# Subtypes, the third taxonomy level, keyed by (category, case_type). Only
# employment is specified so far; validation is by the (type, subtype) pair,
# so a subtype slug shared by two types is only accepted under a type that
# actually lists it. See taxonomy.py and CASE-TAXONOMY.md.
VALID_SUBTYPES = {
    (EMPLOYMENT_CATEGORY, case_type): {slug for slug, _ in subs}
    for case_type, subs in EMPLOYMENT_SUBTYPES.items()
}


def normalize_category(category: str | None) -> str | None:
    """Retell's Selector extraction occasionally tacks on stray punctuation
    ("personal_injury,") or reformats the label ("Family Law"). Collapse to
    the canonical value; anything still unrecognized becomes "other" rather
    than being stored raw, where it would render as Uncategorized and never
    match the dashboard's category filter."""
    if not category:
        return category
    cleaned = _clean_slug(category)
    return cleaned if cleaned in VALID_CATEGORIES else "other"


def normalize_subcategory(subcategory: str | None, category: str | None) -> str | None:
    """Valid subcategory for the given category, or None. Unlike categories
    there is no catch-all to fall back to — a subcategory that doesn't match
    the list is dropped, since a wrong specific label ("divorce" on a
    custody matter) is worse than none."""
    if not subcategory:
        return None
    cleaned = _clean_slug(subcategory)
    return cleaned if cleaned in VALID_SUBCATEGORIES.get(category or "", ()) else None


def normalize_subtype(
    subtype: str | None, category: str | None, case_type: str | None
) -> str | None:
    """Valid subtype for the given (category, case_type), or None. Validated
    against the pair — a subtype only counts under a case type that actually
    lists it. Dropped rather than stored raw, like subcategory."""
    if not subtype:
        return None
    cleaned = _clean_slug(subtype)
    allowed = VALID_SUBTYPES.get((category or "", case_type or ""), ())
    return cleaned if cleaned in allowed else None


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


# Thresholds for matching a caller's spoken name against the name on file.
# Whole-name comparison ignores spacing, so it is the looser of the two; a
# single name part is much shorter, where a small edit is proportionally a
# bigger difference, so it has to clear a higher bar.
_NAME_SIMILARITY = 0.80
_TOKEN_SIMILARITY = 0.85
# Shortest fragment allowed to match on its own. Exact matches on a whole
# name part are exempt — plenty of real first names are shorter than this.
_MIN_PARTIAL = 4


def _squash(name: str) -> str:
    """Lowercase letters only — no spaces, punctuation, or digits."""
    return re.sub(r"[^a-z]", "", name.lower())


def name_matches(given: str | None, on_file: str | None) -> bool:
    """Does the name a caller gave plausibly match the name on their case?

    Both sides of this comparison came through a phone line, so neither is
    trustworthy character-for-character. One caller has reached us as
    "Guruprakash", "Guna Prakash", and "Kunal Prahash" across three calls —
    the same person each time. A plain substring test fails all of those:
    the space in "Guna Prakash" alone is enough to reject "Gunaprakash".

    So compare three ways, cheapest first:
      1. the whole name with spacing removed, fuzzily — catches a name
         merged, split, or misheard by a couple of letters;
      2. an exact match on any one name part — a caller who gives only
         "Alex" for "Alex Rivera", which is normal and expected;
      3. a name part that is close enough to one on file, or contained in
         it, provided it is long enough to mean something.

    A minimum length applies to everything except an exact name-part match.
    Without it the old check accepted "a" for "Maria Santos", which made the
    name useless as a second identity factor.
    """
    if not given or not on_file:
        return False

    squashed_given, squashed_file = _squash(given), _squash(on_file)
    if not squashed_given or not squashed_file:
        return False

    if SequenceMatcher(None, squashed_given, squashed_file).ratio() >= _NAME_SIMILARITY:
        return True

    given_parts = [p for p in (_squash(p) for p in given.split()) if p]
    file_parts = [p for p in (_squash(p) for p in on_file.split()) if p]

    for part in given_parts:
        if part in file_parts:
            return True
        if len(part) < _MIN_PARTIAL:
            continue
        if part in squashed_file:
            return True
        for other in file_parts:
            if SequenceMatcher(None, part, other).ratio() >= _TOKEN_SIMILARITY:
                return True

    return False


# Fragments of the agent's own scripted closing lines, used to work out how
# a call ended. Retell's own call_outcome extraction field has been observed
# to mislabel calls (e.g. reporting "completed" on a call that ended with the
# nonsensical-caller script), so this reads the transcript directly instead.
#
# Several fragments per outcome, deliberately: the model paraphrases rather
# than reciting the script verbatim. Real observed variations include
# "I may not be following you clearly" for the scripted "having a hard time
# following the details", and "might not be the best time to go through all
# the questions" for "the right time to go through these details". Matching
# one exact sentence per ending missed ~22% of calls.
#
# Keep these in sync with the closing lines in agent-prompt-latest.txt —
# if the prompt's wording changes and these don't, routing silently falls
# back to Retell's less reliable classification.
_OUTCOME_PATTERNS = [
    ("emergency", (
        "call 911",
        "your safety comes first",
        "local emergency number",
    )),
    # Genuine callers who reached the wrong business (a coding question, a
    # pricing question). Checked before the "difficult caller" endings below
    # because these people are polite and coherent — they just need somewhere
    # other than the attorney review queue.
    ("out_of_scope", (
        "isn't something our law office",
        "not something our law office",
        "only handle legal matters",
        "not the right place for",
        "not something we can help with",
        "not the right office",
    )),
    ("unwanted", (
        "hard time following",
        "following you clearly",
        "trouble following",
    )),
    ("spam", (
        "right time to go through",
        "best time to go through",
        "right time to go over",
    )),
    ("partial", (
        "gotten disconnected",
        "able to hear me",
        "may have lost you",
    )),
    ("completed", (
        "have everything i need",
    )),
]

# How many of the agent's final lines to inspect. More than one because a
# single spoken sentence is sometimes split across lines in the transcript
# when the caller interrupts mid-sentence.
_CLOSING_LINES_TO_CHECK = 3


def detect_outcome_from_transcript(transcript: str | None) -> str | None:
    """Returns one of "emergency"/"unwanted"/"spam"/"partial"/"completed" by
    matching the agent's own scripted closing lines, or None if the call
    didn't end with any recognized script (e.g. it dropped for a reason
    outside the agent's control, or the agent improvised an ending).

    Only the agent's closing lines are searched — scanning the whole
    transcript would let a caller's own words ("should I call 911?") decide
    how the call gets filed.
    """
    if not transcript:
        return None

    agent_lines = [
        line.split(":", 1)[1].strip()
        for line in transcript.split("\n")
        if line.strip().lower().startswith("agent:")
    ]
    if not agent_lines:
        return None

    closing = " ".join(agent_lines[-_CLOSING_LINES_TO_CHECK:]).lower()
    for outcome, fragments in _OUTCOME_PATTERNS:
        if any(fragment in closing for fragment in fragments):
            return outcome
    return None
