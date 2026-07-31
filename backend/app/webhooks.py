import base64
import json
import os
import uuid

from fastapi import APIRouter, Request, Response

from .db import find_caller_history, upsert_record
from .security import verify_signature
from .validators import detect_outcome_from_transcript, is_valid_email, is_valid_phone, normalize_category

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

    return {
        "call_inbound": {
            "dynamic_variables": {
                "caller_known": "true" if most_recent else "false",
                "previous_case_category": most_recent["case_category"] if most_recent else "",
                "previous_case_summary": most_recent["case_summary"] if most_recent else "",
            }
        }
    }


@router.post("/webhooks/retell")
async def post_call(request: Request):
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

    if event == "call_analyzed":
        analysis = call.get("call_analysis", {}) or {}
        d = analysis.get("custom_analysis_data", {}) or {}

        emergency_flagged = int(bool(d.get("emergency_flagged")))
        case_category = normalize_category(d.get("case_category"))
        required = (d.get("caller_name"), d.get("callback_phone"), case_category, d.get("case_summary"))
        is_complete = all(required)

        # Primary signal: search the transcript for the agent's own scripted
        # closing lines, which we control exactly — deterministic, unlike
        # Retell's call_outcome Post-Call Data Extraction field, which has
        # repeatedly mislabeled calls as "completed" even when the
        # transcript contains a different scripted ending verbatim.
        # call_outcome is only consulted as a fallback for "unwanted"/"spam"
        # when the transcript itself is missing (shouldn't normally happen).
        transcript_outcome = detect_outcome_from_transcript(call.get("transcript"))
        outcome = d.get("call_outcome")

        if emergency_flagged or transcript_outcome == "emergency":
            table = "emergency_flags"
        elif transcript_outcome == "unwanted" or (transcript_outcome is None and outcome == "unwanted"):
            table = "unwanted_calls"
        elif transcript_outcome == "spam" or (transcript_outcome is None and outcome == "spam"):
            table = "spam_calls"
        elif is_complete:
            table = "cases"
        else:
            table = "partial_calls"

        phone_valid = is_valid_phone(d.get("callback_phone"))
        email_valid = is_valid_email(d.get("email"))

        row = {
            "id": str(uuid.uuid4()),
            "call_id": call.get("call_id"),
            "from_number": call.get("from_number"),
            "case_category": case_category,
            "caller_name": d.get("caller_name"),
            "callback_phone": d.get("callback_phone"),
            "is_phone_valid": None if phone_valid is None else int(phone_valid),
            "email": d.get("email"),
            "is_email_valid": None if email_valid is None else int(email_valid),
            "incident_date": d.get("incident_date"),
            "location": d.get("location"),
            "opposing_party": d.get("opposing_party"),
            "key_date_or_deadline": d.get("key_date_or_deadline"),
            "represented_already": int(bool(d.get("represented_already"))),
            "injured": int(bool(d.get("injured"))),
            "emergency_flagged": emergency_flagged,
            "police_report_filed": int(bool(d.get("police_report_filed"))),
            "case_summary": d.get("case_summary"),
            "additional_details": d.get("additional_details"),
            "call_summary": analysis.get("call_summary"),
            "call_successful": str(analysis.get("call_successful", "")),
            "user_sentiment": analysis.get("user_sentiment"),
            "transcript": call.get("transcript"),
            "recording_url": call.get("recording_url"),
        }

        upsert_record(table, row)

    return Response(status_code=204)
