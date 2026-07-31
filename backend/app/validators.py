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
