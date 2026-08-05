import base64
import json
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Request, Response

from .classify import classify_and_store
from .db import find_caller_history, find_staff_phone, staff_directory_line, upsert_record
from .intake_fields import ALL_FIELDS, REQUIRED_FOR_CASE
from .security import verify_signature
from .validators import (
    coerce_bool,
    coerce_text,
    derive_time_sensitive,
    detect_outcome_from_transcript,
    is_valid_email,
    is_valid_phone,
    normalize_category,
    normalize_subcategory,
)

router = APIRouter()

# TEMPORARY — captures the last raw webhook attempt for debugging signature
# mismatches. Remove _last_attempt and the /debug/last-webhook route below
# once verification is confirmed working against a real Retell request.
_last_attempt: dict = {}


@router.post("/webhooks/retell/inbound")
async def inbound(request: Request):
    """Fires the instant a call connects, before the agent speaks.
    Must respond quickly with JSON — used to greet returning callers."""
    payload = await request.json()
    from_number = payload.get("call_inbound", {}).get("from_number")

    history = find_caller_history(from_number) if from_number else []
    most_recent = history[0] if history else None

    # Who, if anyone, this caller's matter is already assigned to. Resolved
    # to a number here rather than in Retell so the directory lives in one
    # place: edit a person in the dashboard and the next call routes to the
    # new number, with nothing to change in the Retell console.
    assigned_to = (most_recent or {}).get("assigned_to") or ""
    assigned_phone = find_staff_phone(assigned_to) or ""

    # Dynamic variables must always be strings — a partial call has no
    # category or summary on file (NULL in the DB), and letting a JSON null
    # or the text "None" through would end up spoken in the greeting.
    return {
        "call_inbound": {
            "dynamic_variables": {
                "caller_known": "true" if most_recent else "false",
                "previous_case_category": (most_recent or {}).get("case_category") or "",
                "previous_case_summary": (most_recent or {}).get("case_summary") or "",
                "previous_case_number": (most_recent or {}).get("case_number") or "",
                # Blank when the matter is unassigned, or when the assigned
                # name has no active directory entry — the routing prompt
                # treats an empty destination as "don't transfer", which is
                # the safe reading of "we don't know who to put you through
                # to".
                "assigned_attorney": assigned_to if assigned_phone else "",
                "assigned_attorney_phone": assigned_phone,
                "staff_directory": staff_directory_line(),
            }
        }
    }


@router.post("/webhooks/retell")
async def post_call(request: Request, background: BackgroundTasks):
    """Fires for call_started / call_ended / call_analyzed.
    Only call_analyzed carries the structured Post-Call Data Extraction fields."""
    raw_body = await request.body()
    signature = request.headers.get("x-retell-signature")
    api_key = os.getenv("RETELL_API_KEY", "").strip()

    verified = verify_signature(raw_body, api_key, signature)
    _last_attempt.update({
        "signature_header": signature,
        "body_length": len(raw_body),
        "body_base64": base64.b64encode(raw_body).decode(),
        "api_key_length": len(api_key or ""),
        "verified": verified,
    })

    if not verified:
        return Response(status_code=401)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return Response(status_code=400)

    event = payload.get("event")
    call = payload.get("call", {})

    # call_id is the primary key for every bucket; without one there is
    # nothing to store the record under, and inserting would crash on the
    # NOT NULL constraint and hand Retell a 500.
    if event == "call_analyzed" and not call.get("call_id"):
        return Response(status_code=204)

    if event == "call_analyzed":
        analysis = call.get("call_analysis", {}) or {}
        d = analysis.get("custom_analysis_data", {}) or {}

        case_category = normalize_category(d.get("case_category"))
        case_subcategory = normalize_subcategory(d.get("case_subcategory"), case_category)

        # Every intake field the agent prompt collects, coerced by its
        # declared type. Booleans are three-state: a field the call never
        # captured stays NULL rather than becoming a "no". See
        # app/intake_fields.py for the spec these come from.
        fields = {
            f.name: (coerce_bool(d.get(f.name)) if f.kind == "bool" else coerce_text(d.get(f.name)))
            for f in ALL_FIELDS
        }
        fields["time_sensitive"] = derive_time_sensitive(
            d.get("time_sensitive"), case_category, fields
        )
        # The one boolean kept two-state: it decides which bucket the call
        # lands in, and "we couldn't tell" has to mean "no safety event".
        emergency_flagged = 1 if fields.get("emergency_flagged") == 1 else 0
        fields["emergency_flagged"] = emergency_flagged

        # Enough to be a case an attorney can act on: who called, how to
        # reach them, what kind of matter, and what happened. The rest of the
        # prompt's must-ask list is reported per record rather than gating
        # the bucket — see intake_fields.missing_must_ask.
        captured = {**fields, "case_category": case_category}
        is_complete = all(captured.get(name) for name in REQUIRED_FOR_CASE)

        # Primary signal: search the transcript for the agent's own scripted
        # closing lines, which we control exactly — deterministic, unlike
        # Retell's call_outcome Post-Call Data Extraction field, which has
        # repeatedly mislabeled calls as "completed" even when the
        # transcript contains a different scripted ending verbatim.
        # call_outcome is only consulted as a fallback for "unwanted"/"spam"
        # when the transcript itself is missing (shouldn't normally happen).
        transcript_outcome = detect_outcome_from_transcript(call.get("transcript"))
        outcome = d.get("call_outcome")

        # A safety event only takes the call out of the attorney queue when it
        # actually ended the call, or when the intake never finished. The
        # prompt has one branch — a whistleblower who says they are being
        # threatened — where the agent checks on the caller's safety and then
        # carries on with the whole intake once they confirm they're safe.
        # Filing that finished intake under emergency_flags alone would hide a
        # complete case from the attorneys who need it, so it goes to `cases`
        # with emergency_flagged set and shows as flagged there.
        if transcript_outcome == "emergency" or (emergency_flagged and not is_complete):
            table = "emergency_flags"
        elif transcript_outcome == "out_of_scope":
            table = "out_of_scope_calls"
        elif transcript_outcome == "unwanted" or (transcript_outcome is None and outcome == "unwanted"):
            table = "unwanted_calls"
        elif transcript_outcome == "spam" or (transcript_outcome is None and outcome == "spam"):
            table = "spam_calls"
        elif is_complete:
            table = "cases"
        else:
            table = "partial_calls"

        phone_valid = is_valid_phone(fields.get("callback_phone"))
        email_valid = is_valid_email(fields.get("email"))

        row = {
            "id": str(uuid.uuid4()),
            "call_id": call.get("call_id"),
            "from_number": call.get("from_number"),
            "case_category": case_category,
            "case_subcategory": case_subcategory,
            "is_phone_valid": None if phone_valid is None else int(phone_valid),
            "is_email_valid": None if email_valid is None else int(email_valid),
            **fields,
            "call_summary": analysis.get("call_summary"),
            "call_successful": str(analysis.get("call_successful", "")),
            "user_sentiment": analysis.get("user_sentiment"),
            "transcript": call.get("transcript"),
            "recording_url": call.get("recording_url"),
        }

        upsert_record(table, row)

        # Completed intakes get an LLM pass that fills the matter type from
        # the transcript. Runs in the background so it never delays this
        # webhook's response; it's a no-op for "other", for already-classified
        # cases, and when no GEMINI_API_KEY is set. See app/classify.py.
        if table == "cases":
            background.add_task(classify_and_store, "cases", call.get("call_id"))

    return Response(status_code=204)
