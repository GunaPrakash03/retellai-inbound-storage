"""Post-call LLM classification into the case taxonomy, using Gemini.

Fills the matter type (case_subcategory) from the call transcript for every
practice area that has one. Runs after the webhook has stored the record, as
a background step, so it never affects the live call or the webhook response.

Deliberately defensive: no API key, a network error, a bad response, or an
off-taxonomy answer all degrade to leaving the field blank. The case still
lands correctly by practice area.

Uses the Gemini REST API over stdlib urllib — no SDK dependency. Configure
with GEMINI_API_KEY (required to classify) and optionally GEMINI_MODEL
(default gemini-2.5-flash).
"""
import json
import os
import time
import urllib.error
import urllib.request

from . import db
from . import taxonomy
from .taxonomy import slugify
from .validators import VALID_SUBCATEGORIES

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_DEFAULT_MODEL = "gemini-2.5-flash"
_TIMEOUT_S = 20
_NONE = "None"  # sentinel enum value — Gemini enums can't express null cleanly

# Below this, store nothing — a weak guess is worse than a blank field.
_MIN_CONFIDENCE = 0.4

# Retry these transient Gemini statuses (rate limit / overloaded) before
# giving up, so one throttled call doesn't silently blank a classification.
_RETRY_STATUSES = {429, 503, 500}
_MAX_ATTEMPTS = 3

# Reason the most recent _gemini() gave up, surfaced by diagnose() so a live
# check can tell a rate limit ("http_429") from a timeout or a missing key.
_LAST_ERROR: str | None = None


# --------------------------------------------------------------- HTTP ------

def _post(model: str, api_key: str, body: dict) -> tuple[dict | None, str | None]:
    """POST to Gemini. Returns (payload, error) — error is a short reason
    string ('http_429', 'timeout', 'neterr_*', 'bad_json') on failure."""
    req = urllib.request.Request(
        _ENDPOINT.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except TimeoutError:
        return None, "timeout"
    except urllib.error.URLError as e:
        return None, f"neterr_{getattr(e, 'reason', '')}".strip("_")
    except ValueError:
        return None, "bad_json"


def _extract_json(payload: dict | None) -> dict | None:
    """Pull the model's JSON object out of a Gemini response, tolerating a
    ```json fence."""
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") : text.rfind("}") + 1]
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        return None


def _attempt(model: str, api_key: str, body: dict) -> dict | None:
    """One request body, retried through transient statuses. Records the last
    failure reason in _LAST_ERROR."""
    global _LAST_ERROR
    for i in range(_MAX_ATTEMPTS):
        payload, err = _post(model, api_key, body)
        result = _extract_json(payload)
        if result is not None:
            _LAST_ERROR = None
            return result
        _LAST_ERROR = err or "empty_response"
        status = int(err[5:]) if err and err.startswith("http_") else None
        if status in _RETRY_STATUSES and i < _MAX_ATTEMPTS - 1:
            time.sleep(2 * (i + 1))  # 2s, 4s backoff
            continue
        break
    return None


def _gemini(prompt: str, schema: dict) -> dict | None:
    """One Gemini classification. Tries the constrained-enum schema first
    (with retries on rate limits); if that request keeps failing — e.g. a
    schema-format quirk — falls back to plain JSON with the allowed values
    still spelled out in the prompt."""
    global _LAST_ERROR
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        _LAST_ERROR = "no_key"
        return None
    model = os.getenv("GEMINI_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    contents = {"contents": [{"parts": [{"text": prompt}]}]}

    with_schema = {
        **contents,
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
    }
    result = _attempt(model, api_key, with_schema)
    if result is not None:
        return result

    plain = {**contents, "generationConfig": {"responseMimeType": "application/json"}}
    return _attempt(model, api_key, plain)


def _confidence(answer: dict) -> float:
    try:
        return float(answer.get("confidence", 0))
    except (TypeError, ValueError):
        return 0.0


# -------------------------------- matter type, any practice area ----------

def _subcategory_schema(slugs: list[str]) -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "matter_type": {"type": "STRING", "enum": slugs + [_NONE]},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["matter_type", "confidence"],
    }


def _subcategory_prompt(
    category: str, choices: list[tuple[str, str]], transcript: str, case_summary: str | None
) -> str:
    options = "\n".join(f"- {slug}  ({label})" for slug, label in choices)
    area = taxonomy.CATEGORY_LABELS.get(category, category.replace("_", " "))
    return (
        f"You classify a US shareholder, whistleblower, or consumer litigation "
        f"intake call in the {area} practice area into its matter type. "
        "Choose the single best matter_type "
        f'value from the list. If nothing fits well, answer "{_NONE}". Never '
        "invent a value not listed. Return JSON with keys matter_type, "
        "confidence (0..1). Answer with the value on the left (the slug).\n\n"
        f"Matter types (value  (description)):\n{options}\n\n"
        f"Case summary: {case_summary or '(none)'}\n\n"
        f"Transcript:\n{transcript}"
    )


def _validate_subcategory(answer: dict | None, category: str) -> str | None:
    if not answer or _confidence(answer) < _MIN_CONFIDENCE:
        return None
    raw = answer.get("matter_type")
    if raw in (None, _NONE):
        return None
    raw = str(raw)
    valid = VALID_SUBCATEGORIES.get(category, set())
    if raw in valid:  # the model returned the slug, as asked
        return raw
    cleaned = slugify(raw)  # tolerate a label if it returned one
    return cleaned if cleaned in valid else None


def classify_subcategory(
    category: str, transcript: str | None, case_summary: str | None
) -> str | None:
    choices = taxonomy.subcategory_choices(category)
    if not choices or not transcript:
        return None
    slugs = [s for s, _ in choices]
    answer = _gemini(
        _subcategory_prompt(category, choices, transcript, case_summary),
        _subcategory_schema(slugs),
    )
    return _validate_subcategory(answer, category)


# ------------------------------------------------------- orchestration -----

def classify_and_store(table: str, call_id: str) -> None:
    """Classify one stored case and write the result. Called as a background
    task from the webhook. No-op when the category has no matter-type list
    ("other"), when it's already classified, or when a human has corrected the
    fields — so redeliveries don't re-call the API and staff edits stand."""
    record = db.get_record(table, call_id)
    if not record:
        return
    category = record.get("case_category")
    if "case_subcategory" in db._manual_edits(record):
        return
    if record.get("case_subcategory"):
        return  # already has a matter type (from Retell or a prior run)
    if not taxonomy.subcategory_choices(category):
        return  # "other", or an area with no matter types

    subcategory = classify_subcategory(
        category, record.get("transcript"), record.get("case_summary")
    )
    if subcategory:
        db.set_classification(table, call_id, subcategory)


def diagnose(category: str | None, transcript: str | None, case_summary: str | None) -> dict:
    """One classification with the internals exposed — for the DEBUG endpoint.
    Shows the key state, the model, Gemini's raw answer, and the validated
    result, so a live check can tell "working" from "key missing" or "answer
    dropped by validation"."""
    key_set = bool(os.getenv("GEMINI_API_KEY", "").strip())
    model = os.getenv("GEMINI_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    raw: dict | None = None
    subcategory = None

    choices = taxonomy.subcategory_choices(category or "")
    if key_set and transcript and choices:
        raw = _gemini(
            _subcategory_prompt(category or "", choices, transcript, case_summary),
            _subcategory_schema([s for s, _ in choices]),
        )
        subcategory = _validate_subcategory(raw, category or "")

    return {
        "gemini_key_set": key_set,
        "model": model,
        "raw_answer": raw,
        "last_error": None if raw is not None else _LAST_ERROR,
        "validated": {"case_subcategory": subcategory},
    }
