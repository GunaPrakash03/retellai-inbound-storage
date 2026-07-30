import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import get_case, list_cases, update_status
from .schemas import StatusUpdate
from .webhooks import router as webhook_router

app = FastAPI(title="Retell Intake Backend")
app.state.retell_api_key = os.getenv("RETELL_API_KEY", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/cases")
def get_cases(limit: int = 50, category: str | None = None, status: str | None = None):
    return list_cases(limit=limit, category=category, status=status)


@app.post("/debug/seed")
def debug_seed():
    """TEMPORARY — inserts one sample case so the frontend can be verified
    against live data before real Retell calls are flowing. Remove this
    endpoint once that's confirmed; it has no auth."""
    import uuid

    from .db import upsert_case

    upsert_case({
        "id": str(uuid.uuid4()),
        "call_id": "debug-seed-001",
        "from_number": "+15555550123",
        "case_category": "personal_injury",
        "caller_name": "Test Caller",
        "callback_phone": "+15555550123",
        "email": "test@example.com",
        "incident_date": "2026-07-28",
        "location": "Austin, TX",
        "opposing_party": "Other driver",
        "key_date_or_deadline": None,
        "represented_already": 0,
        "injured": 1,
        "emergency_flagged": 0,
        "police_report_filed": 1,
        "case_summary": "Rear-ended at a red light, minor whiplash — seeded for testing.",
        "additional_details": "This row was created by /debug/seed to verify the dashboard is live.",
        "call_summary": "Test call summary.",
        "call_successful": "True",
        "user_sentiment": "Neutral",
        "transcript": "Caller: This is a test call.\nMaya: Got it, thanks for confirming the pipeline works.",
        "recording_url": None,
    })
    return {"seeded": True, "call_id": "debug-seed-001"}


@app.get("/cases/{call_id}")
def get_case_detail(call_id: str):
    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return row


@app.patch("/cases/{call_id}")
def patch_case_status(call_id: str, body: StatusUpdate):
    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    update_status(call_id, body.status)
    return get_case(call_id)
