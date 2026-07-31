import os

from dotenv import load_dotenv

load_dotenv()

import hmac
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .db import get_case, get_record, list_cases, list_records, update_record_status, update_status
from .schemas import (
    AssignmentUpdate,
    CourtStatusUpdate,
    MessageCreate,
    MessageUpdate,
    StaffCreate,
    StaffUpdate,
    StatusUpdate,
)
from .security import SlidingWindowLimiter, verify_signature
from .webhooks import _last_attempt, router as webhook_router

app = FastAPI(title="Retell Intake Backend")

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


@app.get("/counts")
def get_counts():
    """Row counts per bucket, plus undelivered messages — one request so the
    dashboard nav doesn't poll every bucket individually."""
    counts = {t: db.count_records(t) for t in db.BUCKETS}
    counts["messages_undelivered"] = db.count_undelivered_messages()
    return counts


@app.get("/cases")
def get_cases(limit: int = 50, category: str | None = None, status: str | None = None):
    return list_cases(limit=limit, category=category, status=status)


# The /debug routes exist only when DEBUG_ENDPOINTS=1 is set. They are
# unauthenticated, and /debug/last-webhook echoes the full raw webhook body —
# a real call's transcript, name, and phone number — so they must never be
# reachable on a deployment holding client data unless actively debugging.
def _require_debug():
    if os.getenv("DEBUG_ENDPOINTS", "").strip() != "1":
        raise HTTPException(status_code=404, detail="Not Found")


@app.get("/debug/last-webhook")
def debug_last_webhook():
    """TEMPORARY — inspect the last webhook attempt to diagnose signature
    mismatches. Does not expose the API key itself, only its length."""
    _require_debug()
    return _last_attempt or {"message": "no webhook attempt received yet"}


@app.post("/debug/seed")
def debug_seed():
    """Populate every table — all six call buckets, staff, messages, plus
    assignments and court statuses — with realistic sample data for testing
    the dashboard and the case-lookup flow. Idempotent; see app/seeding.py."""
    _require_debug()
    from .seeding import seed_all

    return seed_all()


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


# ------------------------------------------------------------- staff ------
# Declared before the generic /{bucket} routes at the bottom of this file,
# which would otherwise swallow /staff and /messages.

@app.get("/staff")
def get_staff_list(active_only: bool = False):
    return db.list_staff(active_only=active_only)


@app.post("/staff", status_code=201)
def post_staff(body: StaffCreate):
    return db.create_staff(body.name, body.role, body.phone, body.extension)


@app.patch("/staff/{staff_id}")
def patch_staff(staff_id: str, body: StaffUpdate):
    if not db.get_staff(staff_id):
        raise HTTPException(status_code=404, detail="Staff member not found")
    return db.update_staff(staff_id, body.model_dump(exclude_unset=True))


@app.delete("/staff/{staff_id}", status_code=204)
def remove_staff(staff_id: str):
    if not db.get_staff(staff_id):
        raise HTTPException(status_code=404, detail="Staff member not found")
    db.delete_staff(staff_id)


# ---------------------------------------------------------- messages ------

@app.get("/messages")
def get_messages(delivered: bool | None = None, limit: int = 100):
    return db.list_messages(delivered=delivered, limit=limit)


@app.post("/messages", status_code=201)
def post_message(body: MessageCreate):
    # A message for a staff member who doesn't exist would sit in the queue
    # addressed to nobody — the join shows a blank name and it's never
    # delivered. Reject it so the caller (agent or dashboard) can recover.
    if body.for_staff_id and not db.get_staff(body.for_staff_id):
        raise HTTPException(status_code=422, detail="Unknown for_staff_id")
    return db.create_message(
        message_text=body.message_text,
        call_id=body.call_id,
        case_number=body.case_number,
        caller_name=body.caller_name,
        callback_phone=body.callback_phone,
        for_staff_id=body.for_staff_id,
    )


@app.patch("/messages/{message_id}")
def patch_message(message_id: str, body: MessageUpdate):
    updated = db.mark_message_delivered(message_id, body.delivered)
    if not updated:
        raise HTTPException(status_code=404, detail="Message not found")
    return updated


# ------------------------------------------------------- case lookup ------

# Lookup limits. Legitimate traffic arrives from Retell's servers, so several
# concurrent callers can share one client IP — the per-IP numbers are sized
# for that, not for one human. The failed-lookup cutoff is the one doing the
# real work: a caller misreading their own number fails twice; someone
# guessing numbers fails hundreds of times.
_LOOKUP_PER_IP_PER_MIN = 20
_LOOKUP_GLOBAL_PER_MIN = 60
_LOOKUP_FAILS_PER_IP_PER_HOUR = 30

_lookup_ip_limit = SlidingWindowLimiter(_LOOKUP_PER_IP_PER_MIN, 60)
_lookup_global_limit = SlidingWindowLimiter(_LOOKUP_GLOBAL_PER_MIN, 60)
_lookup_fail_limit = SlidingWindowLimiter(_LOOKUP_FAILS_PER_IP_PER_HOUR, 3600)


def _client_ip(request: Request) -> str:
    # Rightmost X-Forwarded-For entry is the one appended by our own proxy;
    # earlier entries are caller-controlled, and trusting them would let
    # per-IP limits be dodged by rotating fake addresses.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _lookup_authorized(request: Request, raw_body: bytes) -> bool:
    """Auth for the lookup endpoint, which discloses case details.

    Accepts either a valid Retell signature — custom-function requests carry
    the same X-Retell-Signature header as webhooks do — or a static shared
    key sent as an X-API-Key custom header configured on the Retell function
    (also the manual-testing path). With neither key configured (local dev),
    the endpoint is open, like the rest of the API.
    """
    retell_key = os.getenv("RETELL_API_KEY", "").strip()
    shared_key = os.getenv("CASE_LOOKUP_API_KEY", "").strip()
    if not retell_key and not shared_key:
        return True
    if retell_key and verify_signature(
        raw_body, retell_key, request.headers.get("x-retell-signature")
    ):
        return True
    given = request.headers.get("x-api-key", "")
    return bool(shared_key) and hmac.compare_digest(given.encode(), shared_key.encode())


@app.post("/case-lookup")
async def case_lookup(request: Request):
    """Look up a case's court status by the number given to the caller.

    Called by the voice agent mid-call as a Retell custom function. POST
    rather than GET so the case number and caller name don't end up in URLs,
    access logs, or browser history.

    Identity check (D3): the case number **plus** the name on file. A case
    number alone is a weak secret — anyone who overhears one would otherwise
    be read someone else's case details. A wrong number and a failed name
    check return an identical `found: false`, deliberately: distinguishing
    them would let someone probe which case numbers are real.

    Every attempt lands in `lookup_audit`; rate-limited requests are refused
    before touching case data and aren't audited (the limiter denial plus
    the attempts that led to it are evidence enough, and auditing floods
    would bloat the table).
    """
    raw = await request.body()
    ip = _client_ip(request)

    # Flood control first, before any signature work or DB writes. Check
    # both limits before recording either, so a request refused by one
    # doesn't still burn the other's budget — one hammering IP must not
    # eat the global allowance that other callers' lookups come out of.
    if _lookup_global_limit.blocked("all") or _lookup_ip_limit.blocked(ip):
        raise HTTPException(status_code=429, detail="Too many lookups — try again shortly")
    _lookup_global_limit.record("all")
    _lookup_ip_limit.record(ip)

    if not _lookup_authorized(request, raw):
        db.record_lookup(ip, None, None, None, "unauthorized")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=422, detail="Body must be a JSON object")

    # Retell wraps custom-function arguments as {name, call, args}; accept
    # both that shape and flat JSON, so the endpoint works registered as a
    # custom function in either payload mode, and called directly.
    if isinstance(payload.get("args"), dict):
        args = payload["args"]
        call_id = (payload.get("call") or {}).get("call_id")
    else:
        args = payload
        call_id = payload.get("call_id")

    # str() rather than model binding: the LLM sometimes passes a numeric
    # case number as a JSON number, and rejecting that would fail live calls.
    case_number = str(args.get("case_number") or "").strip()
    caller_name = str(args.get("caller_name") or "").strip()
    if not case_number or not caller_name:
        raise HTTPException(
            status_code=422, detail="case_number and caller_name are required"
        )

    if _lookup_fail_limit.blocked(ip):
        raise HTTPException(
            status_code=429, detail="Too many failed lookups — try again later"
        )

    record = db.find_by_case_number(case_number)

    on_file = ((record or {}).get("caller_name") or "").strip().lower()
    given = caller_name.lower()
    # Accept a first name or partial match — callers give "Alex" when the
    # file says "Alex Rivera", and the number is the primary factor here.
    name_ok = bool(on_file) and (given in on_file or on_file in given)

    if not record or not name_ok:
        _lookup_fail_limit.record(ip)
        db.record_lookup(ip, call_id, case_number, caller_name, "not_found")
        return {"found": False}

    db.record_lookup(ip, call_id, case_number, caller_name, "found")
    return {
        "found": True,
        "case_number": record["case_number"],
        "caller_name": record.get("caller_name"),
        "case_category": record.get("case_category"),
        "assigned_to": record.get("assigned_to"),
        "court_status": record.get("court_status"),
        "next_hearing_date": record.get("next_hearing_date"),
        "court_status_updated": record.get("court_status_updated"),
        "has_status": bool(record.get("court_status") or record.get("next_hearing_date")),
    }


@app.get("/lookup-audit")
def get_lookup_audit(limit: int = 100):
    """Recent case-lookup attempts, newest first, for staff review."""
    return db.list_lookup_audit(limit=limit)


# Other call buckets, keyed by URL-friendly name -> table name. "cases" keeps
# its own dedicated routes above for backward compatibility. These generic
# routes are declared last so they never shadow a literal path above them.
BUCKET_TABLES = {
    "partial-calls": "partial_calls",
    "unwanted-calls": "unwanted_calls",
    "spam-calls": "spam_calls",
    "out-of-scope-calls": "out_of_scope_calls",
    "emergency-flags": "emergency_flags",
}


def _bucket_table(bucket: str) -> str:
    table = BUCKET_TABLES.get(bucket)
    if not table:
        raise HTTPException(status_code=404, detail="Unknown call bucket")
    return table


@app.get("/{bucket}")
def get_bucket_records(bucket: str, limit: int = 50, category: str | None = None, status: str | None = None):
    return list_records(_bucket_table(bucket), limit=limit, category=category, status=status)


@app.get("/{bucket}/{call_id}")
def get_bucket_record_detail(bucket: str, call_id: str):
    row = get_record(_bucket_table(bucket), call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return row


@app.patch("/{bucket}/{call_id}")
def patch_bucket_record_status(bucket: str, call_id: str, body: StatusUpdate):
    table = _bucket_table(bucket)
    row = get_record(table, call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    update_record_status(table, call_id, body.status)
    return get_record(table, call_id)


def _any_bucket_table(bucket: str) -> str:
    """Resolve a URL bucket name to a table, including plain "cases"."""
    if bucket == "cases":
        return "cases"
    return _bucket_table(bucket)


# Three-segment paths, so they don't collide with /{bucket}/{call_id} above.

@app.patch("/{bucket}/{call_id}/assignment")
def patch_assignment(bucket: str, call_id: str, body: AssignmentUpdate):
    table = _any_bucket_table(bucket)
    if not get_record(table, call_id):
        raise HTTPException(status_code=404, detail="Record not found")
    db.set_case_assignment(table, call_id, body.assigned_to)
    return get_record(table, call_id)


@app.patch("/{bucket}/{call_id}/court-status")
def patch_court_status(bucket: str, call_id: str, body: CourtStatusUpdate):
    table = _any_bucket_table(bucket)
    if not get_record(table, call_id):
        raise HTTPException(status_code=404, detail="Record not found")
    db.set_court_status(table, call_id, body.court_status, body.next_hearing_date)
    return get_record(table, call_id)
