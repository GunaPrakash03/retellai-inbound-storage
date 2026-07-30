import json
import uuid

from fastapi import APIRouter, Request, Response

from .db import find_caller_history, upsert_case
from .security import verify_signature

router = APIRouter()


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
    api_key = request.app.state.retell_api_key

    if not verify_signature(raw_body, api_key, signature):
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

        upsert_case({
            "id": str(uuid.uuid4()),
            "call_id": call.get("call_id"),
            "from_number": call.get("from_number"),
            "case_category": d.get("case_category"),
            "caller_name": d.get("caller_name"),
            "callback_phone": d.get("callback_phone"),
            "email": d.get("email"),
            "incident_date": d.get("incident_date"),
            "location": d.get("location"),
            "opposing_party": d.get("opposing_party"),
            "key_date_or_deadline": d.get("key_date_or_deadline"),
            "represented_already": int(bool(d.get("represented_already"))),
            "injured": int(bool(d.get("injured"))),
            "emergency_flagged": int(bool(d.get("emergency_flagged"))),
            "police_report_filed": int(bool(d.get("police_report_filed"))),
            "case_summary": d.get("case_summary"),
            "additional_details": d.get("additional_details"),
            "call_summary": analysis.get("call_summary"),
            "call_successful": str(analysis.get("call_successful", "")),
            "user_sentiment": analysis.get("user_sentiment"),
            "transcript": call.get("transcript"),
            "recording_url": call.get("recording_url"),
        })

    return Response(status_code=204)
