import os

from dotenv import load_dotenv

load_dotenv()

import hmac
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from . import db, intake_fields
from .db import get_case, get_record, list_cases, list_records, update_record_status, update_status
from .schemas import (
    AssignmentUpdate,
    CourtStatusUpdate,
    MessageCreate,
    MessageUpdate,
    RecordFieldsUpdate,
    StaffCreate,
    StaffUpdate,
    StatusUpdate,
)
from .security import SlidingWindowLimiter, verify_signature
from .validators import check_phone, name_matches
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
def get_cases(
    limit: int = 50,
    category: str | None = None,
    status: str | None = None,
    subcategory: str | None = None,
    assigned_to: str | None = None,
):
    return list_cases(
        limit=limit, category=category, status=status,
        subcategory=subcategory, assigned_to=assigned_to,
    )


@app.get("/category-counts")
def get_category_counts():
    """Case count per legal category, for the home page's category list."""
    return db.count_cases_by_category()


@app.get("/taxonomy")
def get_taxonomy():
    """Practice areas and their matter types, so the labels live in one place
    (backend taxonomy.py) rather than being duplicated in the frontend."""
    from . import taxonomy

    return {
        category: {
            "label": taxonomy.CATEGORY_LABELS[category],
            "types": [{"value": v, "label": l} for v, l in taxonomy.subcategory_choices(category)],
        }
        for category, _ in taxonomy.CATEGORIES
    }


@app.get("/intake-fields")
def get_intake_fields():
    """What the agent collects, per practice area — the same spec the schema,
    the webhook, and the Retell extraction config are all generated from.

    The dashboard renders a record's fields from this, so a field added to
    app/intake_fields.py shows up without a frontend change, and `must_ask`
    marks the ones the prompt requires before the agent may close the call.
    """
    return {
        "core": [
            {"name": f.name, "label": f.label, "kind": f.kind, "must_ask": f.must_ask}
            for f in intake_fields.CORE_FIELDS
        ],
        "categories": {
            category: {
                "label": label,
                "fields": [
                    {"name": f.name, "label": f.label, "kind": f.kind, "must_ask": f.must_ask}
                    for f in intake_fields.CATEGORY_FIELDS.get(category, [])
                ],
            }
            for category, label in intake_fields.CATEGORIES
        },
    }


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
def debug_seed(reset: bool = False):
    """Populate every table — one completed case per legal category, one call
    per other bucket, staff, messages, assignments, and court statuses — with
    realistic sample data. Idempotent; see app/seeding.py.

    With ?reset=1, wipes all existing call data first (every bucket, messages,
    and the lookup audit) so only the sample set remains. The staff directory
    is preserved. Destructive and irreversible — DEBUG-gated for that reason."""
    _require_debug()
    from .seeding import seed_all

    return seed_all(reset=reset)


@app.post("/debug/classify/{call_id}")
def debug_classify(call_id: str, store: bool = False):
    """Run the Gemini taxonomy classifier on one existing case and return what
    it saw — the key state, the model, Gemini's raw answer, and the validated
    result — so you can confirm the LLM works end to end without a live call.
    With ?store=1, also writes the result (respecting manual edits)."""
    _require_debug()
    from . import classify

    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    category = row.get("case_category")
    result = classify.diagnose(category, row.get("transcript"), row.get("case_summary"))
    result["case"] = {
        "call_id": call_id,
        "case_category": category,
        "has_transcript": bool(row.get("transcript")),
    }
    if store and (matter_type := result["validated"]["case_subcategory"]):
        db.set_classification("cases", call_id, matter_type)
        result["stored"] = True
    return result


@app.post("/debug/purge")
def debug_purge():
    """Empty the database — every call bucket, messages, and the lookup audit
    — leaving no sample data behind, unlike /debug/seed?reset=1 which
    repopulates. The staff directory is preserved. Destructive and
    irreversible; DEBUG-gated for that reason."""
    _require_debug()
    cleared = db.reset_call_data()
    return {"purged": True, "cleared": cleared}


def _with_intake(row: dict) -> dict:
    """A record plus what the prompt says should be on it.

    `intake` is the labelled field list for this record's practice area, and
    `missing_must_ask` names the must-ask questions that never got captured —
    the prompt's own Step 4 check, applied after the call. Both are derived,
    never stored, so they can't fall behind the spec.
    """
    return {
        **row,
        "intake": intake_fields.field_view(row),
        "missing_must_ask": intake_fields.missing_must_ask(row),
    }


@app.get("/cases/{call_id}")
def get_case_detail(call_id: str):
    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return _with_intake(row)


@app.patch("/cases/{call_id}")
def patch_case_status(call_id: str, body: StatusUpdate):
    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    update_status(call_id, body.status)
    return _with_intake(get_case(call_id))


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


def _retell_args(payload: dict) -> tuple[dict, str | None]:
    """Unwrap a Retell custom-function body.

    Retell sends `{name, call, args}` when a function is registered in one
    payload mode and the bare arguments in the other, and which one you get
    isn't obvious from the console. Accepting both is what keeps a live call
    from failing on a configuration detail. Returns (args, call_id).
    """
    if isinstance(payload.get("args"), dict):
        return payload["args"], (payload.get("call") or {}).get("call_id")
    return payload, payload.get("call_id")


@app.post("/messages", status_code=201)
async def post_message(request: Request):
    """Record a message for a staff member.

    Called by the dashboard with a flat body, and by the voice agent as the
    `take_message` custom function — which is why the body is parsed by hand
    rather than bound to MessageCreate. A live call ended with a 422 here
    because Retell wrapped the arguments as `{name, call, args}` and the
    model, having no arguments to send, sent `args: {}`; the caller was
    promised a callback that was never recorded. A missing message now comes
    back as an instruction the agent can act on instead of a schema error.
    """
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=422, detail="Body must be a JSON object")

    args, wrapper_call_id = _retell_args(payload)
    try:
        body = MessageCreate(**{**args, "call_id": args.get("call_id") or wrapper_call_id})
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail=(
                "message_text is required — ask the caller what they'd like passed "
                "on, and who it's for, then call this again with that text."
            ),
        )

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


@app.post("/validate-phone")
async def validate_phone(request: Request):
    """Count and check a callback number for the agent, mid-call.

    Registered in Retell as the `check_phone_number` custom function. The
    agent sends what it heard — "nine one two three..." or "912-345-6789" —
    and reads back the `say` line rather than counting digits itself, which
    is the one thing it demonstrably cannot do reliably. See
    validators.check_phone.

    Unauthenticated like the rest of the API: it holds no data, reads
    nothing, and writes nothing, so there is nothing here to protect.
    """
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=422, detail="Body must be a JSON object")

    args, _ = _retell_args(payload)
    return check_phone(args.get("phone") or args.get("callback_phone"))


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

# Values the agent sends when it hasn't actually collected the field. Not a
# real answer from the caller, so not a real lookup attempt.
_PLACEHOLDERS = {"unknown", "unspecified", "n/a", "na", "none", "null", "not provided"}

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

    # The agent has called this with the literal string "unknown" in place of
    # a value it hadn't collected yet — the prompt tells it to record unknown
    # fields that way, and it applied that to the arguments. Treat a
    # placeholder as "not asked yet" rather than a failed lookup: a 422 tells
    # the agent to go and ask, and it doesn't spend the caller's
    # failed-lookup budget on a question that was never put to them.
    if case_number.lower() in _PLACEHOLDERS or caller_name.lower() in _PLACEHOLDERS:
        raise HTTPException(
            status_code=422,
            detail="Ask the caller for their case number and name before looking up",
        )

    if _lookup_fail_limit.blocked(ip):
        raise HTTPException(
            status_code=429, detail="Too many failed lookups — try again later"
        )

    record = db.find_by_case_number(case_number)

    # Both names came through a phone line, so neither is reliable
    # character-for-character; see validators.name_matches.
    name_ok = name_matches(caller_name, (record or {}).get("caller_name"))

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


@app.get("/hearings")
def get_hearings(limit: int = 100, upcoming_only: bool = True):
    """Cases with a court date, soonest first — the home page's court calendar.

    Declared above the generic /{bucket} routes so it isn't read as a bucket
    name. Returns only the fields the calendar renders, so the home page
    doesn't pull whole transcripts it will never show.
    """
    rows = db.list_hearings(limit=limit, upcoming_only=upcoming_only)
    return [
        {
            "call_id": r.get("call_id"),
            "case_number": r.get("case_number"),
            "caller_name": r.get("caller_name"),
            "case_category": r.get("case_category"),
            "case_subcategory": r.get("case_subcategory"),
            "next_hearing_date": r.get("next_hearing_date"),
            "hearing_attorney": r.get("hearing_attorney"),
            "court_status": r.get("court_status"),
            "court_status_updated": r.get("court_status_updated"),
            "status": r.get("status"),
        }
        for r in rows
    ]


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
def get_bucket_records(
    bucket: str,
    limit: int = 50,
    category: str | None = None,
    status: str | None = None,
    subcategory: str | None = None,
    assigned_to: str | None = None,
):
    return list_records(
        _bucket_table(bucket), limit=limit, category=category, status=status,
        subcategory=subcategory, assigned_to=assigned_to,
    )


@app.get("/{bucket}/{call_id}")
def get_bucket_record_detail(bucket: str, call_id: str):
    row = get_record(_bucket_table(bucket), call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return _with_intake(row)


@app.patch("/{bucket}/{call_id}")
def patch_bucket_record_status(bucket: str, call_id: str, body: StatusUpdate):
    table = _bucket_table(bucket)
    row = get_record(table, call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    update_record_status(table, call_id, body.status)
    return _with_intake(get_record(table, call_id))


def _any_bucket_table(bucket: str) -> str:
    """Resolve a URL bucket name to a table, including plain "cases"."""
    if bucket == "cases":
        return "cases"
    return _bucket_table(bucket)


# Three-segment paths, so they don't collide with /{bucket}/{call_id} above.

@app.patch("/{bucket}/{call_id}/fields")
def patch_record_fields(bucket: str, call_id: str, body: RecordFieldsUpdate):
    """Correct intake fields the speech-to-text extraction got wrong.

    The mid-call lookup matches a caller against `caller_name`, so a misheard
    name locks that caller out of their own case — this is the route that
    fixes it. Corrections are marked in `manual_edits` and survive webhook
    redelivery; see db.update_record_fields.
    """
    table = _any_bucket_table(bucket)
    if not get_record(table, call_id):
        raise HTTPException(status_code=404, detail="Record not found")
    return _with_intake(db.update_record_fields(table, call_id, body.model_dump(exclude_unset=True)))


@app.patch("/{bucket}/{call_id}/assignment")
def patch_assignment(bucket: str, call_id: str, body: AssignmentUpdate):
    table = _any_bucket_table(bucket)
    if not get_record(table, call_id):
        raise HTTPException(status_code=404, detail="Record not found")
    db.set_case_assignment(table, call_id, body.assigned_to)
    return _with_intake(get_record(table, call_id))


@app.patch("/{bucket}/{call_id}/court-status")
def patch_court_status(bucket: str, call_id: str, body: CourtStatusUpdate):
    table = _any_bucket_table(bucket)
    if not get_record(table, call_id):
        raise HTTPException(status_code=404, detail="Record not found")
    db.set_court_status(
        table, call_id, body.court_status, body.next_hearing_date, body.hearing_attorney
    )
    return _with_intake(get_record(table, call_id))
