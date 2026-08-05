import re
from difflib import SequenceMatcher

from .taxonomy import (
    CATEGORY_LABELS,
    MATTER_TYPES,
    slugify as _clean_slug,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# The ten practice areas in the agent prompt's Step 1. Declared in
# intake_fields.CATEGORIES, next to the fields each area collects.
VALID_CATEGORIES = set(CATEGORY_LABELS)


# Matter types within each practice area — the taxonomy's second level, from
# distinctions the agent prompt itself draws. The extraction can only
# reliably pick values the agent actually asked the questions to
# distinguish. "other" has no list: by definition it holds what didn't fit.
VALID_SUBCATEGORIES = {
    category: {slug for slug, _ in types} for category, types in MATTER_TYPES.items()
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
    """Valid matter type for the given category, or None. Unlike categories
    there is no catch-all to fall back to — a matter type that doesn't match
    the list is dropped, since a wrong specific label ("insider trading" on a
    board-oversight matter) is worse than none."""
    if not subcategory:
        return None
    cleaned = _clean_slug(subcategory)
    return cleaned if cleaned in VALID_SUBCATEGORIES.get(category or "", ()) else None


# What Retell's Boolean extraction (and the LLM behind it) has been seen to
# send in place of a real boolean. Anything not listed here — including the
# "unknown" the prompt tells the agent to record for a question the caller
# couldn't answer — is stored as NULL rather than guessed either way.
_TRUE_WORDS = {"true", "yes", "y", "1"}
_FALSE_WORDS = {"false", "no", "n", "0", "none", "never"}


def coerce_bool(value) -> int | None:
    """A three-state boolean: 1, 0, or None for "never captured".

    None matters as much as the other two. The prompt is explicit that a
    question asked and answered "I don't know" is a different fact from a
    question never asked, and both are different from a "no" — so a missing
    field must not collapse to 0 the way `int(bool(value))` collapses it.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(bool(value))
    text = str(value).strip().lower()
    if not text:
        return None
    if text in _TRUE_WORDS:
        return 1
    if text in _FALSE_WORDS:
        return 0
    return None


def coerce_text(value) -> str | None:
    """Trimmed text, or None for an empty field."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# Phrases a caller's "I haven't reported this anywhere" comes back as. Used
# only to decide whether a whistleblower matter is first-to-file sensitive;
# anything unrecognized is treated as "they have reported it somewhere",
# which is the answer that does *not* raise the flag.
_NOT_YET_REPORTED = {"no", "none", "no one", "nobody", "not yet", "n/a", "na", "never"}


def derive_time_sensitive(flag, category: str | None, fields: dict) -> int | None:
    """Whether this intake is running against a clock.

    The prompt tells the agent to mark `time_sensitive` itself, but that is
    one more thing for the extraction to remember on a call that already
    ended — and the cost of missing it is a lead plaintiff deadline nobody
    saw. So the extraction's own answer is ORed with the four situations the
    prompt names as deadline-driven, each read from a field that is already
    on the record:

      - a securities lead plaintiff deadline the caller read off a notice,
      - a merger vote, tender, or closing date,
      - a retaliation adverse action, whose date starts a filing clock,
      - a whistleblower matter not yet reported anywhere, where being first
        to file can decide the claim.
    """
    captured = coerce_bool(flag)
    if captured == 1:
        return 1

    def has(name: str) -> bool:
        return bool(coerce_text(fields.get(name)))

    derived = False
    if category == "securities_fraud":
        derived = has("lead_plaintiff_deadline")
    elif category == "merger_transaction":
        derived = has("key_date_or_deadline")
    elif category == "whistleblower_retaliation":
        derived = has("incident_date") or has("adverse_action")
    elif category in ("whistleblower_sec", "whistleblower_qui_tam"):
        reported = (coerce_text(fields.get("prior_report")) or "").lower().rstrip(".")
        derived = reported in _NOT_YET_REPORTED or has("key_date_or_deadline")

    if derived:
        return 1
    return captured


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
        "go somewhere safe",
    )),
    # Genuine callers who reached the wrong place — a technical question, a
    # sales question, a wrong number, or a real legal matter in an area this
    # firm doesn't practice. Checked before the "difficult caller" endings
    # below because these people are polite and coherent; they just need
    # somewhere other than the attorney review queue.
    ("out_of_scope", (
        "something our firm can help with",
        "outside what our firm handles",
        "we handle shareholder, whistleblower",
        "we focus on shareholder, whistleblower",
        "bar association",
        "not the right place for",
        # Wording from the previous general-practice prompt, kept so a call
        # recorded against the old agent still files itself correctly.
        "isn't something our law office",
        "not something our law office",
        "only handle legal matters",
        "not something we can help with",
        "not the right office",
    )),
    ("unwanted", (
        "hard time following",
        "following you clearly",
        "trouble following",
        "getting accurate information",
    )),
    ("spam", (
        "right time to go through",
        "best time to go through",
        "right time to go over",
        "ready to share what's going on",
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
