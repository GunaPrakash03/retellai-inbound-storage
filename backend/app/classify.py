"""Post-call LLM classification into the case taxonomy, using Gemini.

Given a completed employment call's transcript, pick the best case type and
subtype from the fixed taxonomy (taxonomy.py). Runs after the webhook has
already stored the record, as a background step — so a slow or failed
classification never affects the live call or the webhook response.

Deliberately defensive: no API key, a network error, a bad response, or an
off-taxonomy answer all degrade to "no subtype". The case still lands
correctly by practice area; only the finer labels are skipped.

Uses the Gemini REST API over stdlib urllib — no SDK dependency to install.
Configure with GEMINI_API_KEY (required to classify) and optionally
GEMINI_MODEL (default gemini-2.5-flash).
"""
import json
import os
import urllib.error
import urllib.request

from . import db
from . import taxonomy
from .validators import EMPLOYMENT_CATEGORY, normalize_subcategory, normalize_subtype

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_DEFAULT_MODEL = "gemini-2.5-flash"
_TIMEOUT_S = 20
_NONE = "None"  # sentinel enum value — Gemini enums can't express null cleanly

# Confidence below this stores no subtype — a weak guess is worse than none.
_MIN_CONFIDENCE = 0.4


def _taxonomy_text() -> str:
    """The employment taxonomy rendered for the prompt: each case type and its
    subtypes, by label."""
    lines = []
    for type_slug, type_label in taxonomy.EMPLOYMENT_TYPES:
        subs = ", ".join(label for _, label in taxonomy.EMPLOYMENT_SUBTYPES[type_slug])
        lines.append(f"- {type_label}: {subs}")
    return "\n".join(lines)


def _response_schema() -> dict:
    type_labels = list(taxonomy.EMPLOYMENT_TYPE_LABELS.values())
    subtype_labels = sorted(set(taxonomy.SUBTYPE_LABELS.values()))
    return {
        "type": "OBJECT",
        "properties": {
            "case_type": {"type": "STRING", "enum": type_labels + [_NONE]},
            "case_subtype": {"type": "STRING", "enum": subtype_labels + [_NONE]},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["case_type", "case_subtype", "confidence"],
    }


def _prompt(transcript: str, case_summary: str | None) -> str:
    return (
        "You classify a US legal intake call into a fixed Workplace & "
        "Employment taxonomy. Choose the single best case type, and the single "
        "best subtype that belongs to that case type. If nothing fits well, "
        f'answer "{_NONE}" for that field. Never invent a value not listed. '
        "Return JSON with keys case_type, case_subtype, confidence (0..1).\n\n"
        f"Taxonomy (case type: its subtypes):\n{_taxonomy_text()}\n\n"
        f"Case summary: {case_summary or '(none)'}\n\n"
        f"Transcript:\n{transcript}"
    )


def _post(model: str, api_key: str, body: dict) -> dict | None:
    req = urllib.request.Request(
        _ENDPOINT.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _extract_json(payload: dict | None) -> dict | None:
    """Pull the model's JSON object out of a Gemini response, tolerating the
    occasional ```json fence."""
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


def _gemini(prompt: str) -> dict | None:
    """One Gemini classification call. Tries the constrained-enum schema first;
    if that request fails (e.g. a schema-format quirk), retries as plain JSON
    with the allowed values still spelled out in the prompt."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    contents = {"contents": [{"parts": [{"text": prompt}]}]}

    with_schema = {
        **contents,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _response_schema(),
        },
    }
    result = _extract_json(_post(model, api_key, with_schema))
    if result is not None:
        return result

    plain = {**contents, "generationConfig": {"responseMimeType": "application/json"}}
    return _extract_json(_post(model, api_key, plain))


def classify_employment(
    transcript: str | None, case_summary: str | None
) -> tuple[str | None, str | None]:
    """Return (case_type_slug, case_subtype_slug) for an employment call, or
    (None, None). Both are validated against the taxonomy, so an off-list or
    mismatched answer is dropped rather than stored."""
    if not transcript:
        return (None, None)
    answer = _gemini(_prompt(transcript, case_summary))
    if not answer:
        return (None, None)

    try:
        confidence = float(answer.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < _MIN_CONFIDENCE:
        return (None, None)

    raw_type = answer.get("case_type")
    raw_subtype = answer.get("case_subtype")
    case_type = normalize_subcategory(
        None if raw_type in (None, _NONE) else str(raw_type), EMPLOYMENT_CATEGORY
    )
    case_subtype = normalize_subtype(
        None if raw_subtype in (None, _NONE) else str(raw_subtype),
        EMPLOYMENT_CATEGORY,
        case_type,
    )
    return (case_type, case_subtype)


def classify_and_store(table: str, call_id: str) -> None:
    """Classify one stored record and write the result. Called as a background
    task from the webhook. No-op unless it's an employment case that hasn't
    been classified or hand-corrected yet — so redeliveries don't re-call the
    API, and staff edits are never overridden."""
    record = db.get_record(table, call_id)
    if not record or record.get("case_category") != EMPLOYMENT_CATEGORY:
        return
    if record.get("case_subtype"):
        return  # already classified
    edited = db._manual_edits(record)
    if "case_subcategory" in edited or "case_subtype" in edited:
        return

    case_type, case_subtype = classify_employment(
        record.get("transcript"), record.get("case_summary")
    )
    if case_type or case_subtype:
        db.set_classification(table, call_id, case_type, case_subtype)
