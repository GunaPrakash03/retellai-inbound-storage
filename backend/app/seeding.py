"""Sample data for every table, used by POST /debug/seed (gated behind
DEBUG_ENDPOINTS=1 in main.py).

The bucket records are shaped exactly like the webhook handler writes them —
full column set, transcripts that end with the agent's scripted closing
lines — so everything downstream (outcome detection, caller history, the
dashboard, case lookup) behaves as it would with real calls.

Idempotent: bucket rows upsert on fixed call_ids and keep their case
numbers; staff are matched by name; messages are only created while the
table is empty.
"""
import uuid

from . import db

# One returning caller: her completed intake and a later dropped call share
# this number, so the inbound webhook greets her as a known caller.
_RETURNING_NUMBER = "+15125559876"


def _row(call_id: str, **overrides) -> dict:
    """A full webhook-shaped row: every updatable column present."""
    row = {c: None for c in db._UPDATABLE_COLUMNS}
    row.update({"id": str(uuid.uuid4()), "call_id": call_id})
    row.update(overrides)
    return row


_BUCKET_ROWS: list[tuple[str, dict]] = [
    ("cases", dict(
        call_id="seed-case-001",
        from_number=_RETURNING_NUMBER,
        case_category="personal_injury",
        caller_name="Maria Santos",
        callback_phone="+15125559876",
        is_phone_valid=1,
        email="maria.santos@example.com",
        is_email_valid=1,
        incident_date="2026-07-18",
        location="Round Rock, TX",
        opposing_party="Delivery van driver",
        represented_already=0,
        injured=1,
        emergency_flagged=0,
        police_report_filed=1,
        case_summary="Rear-ended at a red light by a delivery van; neck and shoulder pain, treated at urgent care.",
        call_summary="Completed intake for a rear-end collision with injuries.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=(
            "User: I was rear-ended at a light last week and my neck still hurts.\n"
            "Agent: I'm sorry to hear that — let me get the details down.\n"
            "User: Sure.\n"
            "Agent: Thank you, Maria. I have everything I need to pass along to our attorneys."
        ),
    )),
    ("cases", dict(
        call_id="seed-case-002",
        from_number="+15125553402",
        case_category="family_law",
        caller_name="James Okafor",
        callback_phone="+15125553402",
        is_phone_valid=1,
        represented_already=0,
        injured=0,
        emergency_flagged=0,
        police_report_filed=0,
        case_summary="Wants to modify a custody arrangement after relocating for work.",
        call_summary="Completed intake for a custody modification.",
        call_successful="True",
        user_sentiment="Positive",
        transcript=(
            "User: I moved for work and need to change our custody schedule.\n"
            "Agent: Understood — a few questions so the right attorney can review it.\n"
            "Agent: Thanks, James. I have everything I need to pass along to our attorneys."
        ),
    )),
    ("cases", dict(
        call_id="seed-case-003",
        from_number="+15125557788",
        case_category="business_contract",
        caller_name="Linh Tran",
        callback_phone="+15125557788",
        is_phone_valid=1,
        represented_already=0,
        injured=0,
        emergency_flagged=0,
        police_report_filed=0,
        case_summary="Client refuses to pay a signed contract's final invoice; dispute over delivered scope.",
        call_summary="Completed intake for an unpaid-invoice contract dispute.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=(
            "User: A client won't pay the last invoice on a signed contract.\n"
            "Agent: Let's capture the details.\n"
            "Agent: Thank you, Linh. I have everything I need to pass along to our attorneys."
        ),
    )),
    ("partial_calls", dict(
        call_id="seed-partial-001",
        from_number=_RETURNING_NUMBER,
        case_category="personal_injury",
        caller_name="Maria Santos",
        emergency_flagged=0,
        case_summary="Called back about the collision case; call dropped before finishing.",
        call_summary="Caller disconnected mid-conversation.",
        call_successful="False",
        user_sentiment="Neutral",
        transcript=(
            "User: Hi, I called before about my accident —\n"
            "Agent: It looks like we may have gotten disconnected. If you can hear me, please call back anytime."
        ),
    )),
    ("partial_calls", dict(
        call_id="seed-partial-002",
        emergency_flagged=0,
        call_summary="Line went silent immediately after connecting.",
        call_successful="False",
        transcript=(
            "Agent: Thanks for calling — this is Maya with the intake team.\n"
            "Agent: It seems you may not be able to hear me. It looks like we may have gotten disconnected."
        ),
    )),
    ("unwanted_calls", dict(
        call_id="seed-unwanted-001",
        emergency_flagged=0,
        case_summary="Caller gave only nonsensical fragments; no coherent matter.",
        call_summary="Nonsensical call; agent ended with the scripted line.",
        call_successful="False",
        user_sentiment="Neutral",
        transcript=(
            "User: Blue elephant. Tuesday. One zero nine.\n"
            "Agent: I'm sorry, but I'm having a hard time following the details. Please call back when it's a better time."
        ),
    )),
    ("spam_calls", dict(
        call_id="seed-spam-001",
        emergency_flagged=0,
        case_summary="Caller repeatedly deflected every intake question.",
        call_summary="Evasive caller; agent closed out with the scripted line.",
        call_successful="False",
        user_sentiment="Negative",
        transcript=(
            "User: I'm not answering that. Next question.\n"
            "Agent: It sounds like this might not be the best time to go through these details. Please call back when it is."
        ),
    )),
    ("out_of_scope_calls", dict(
        call_id="seed-oos-001",
        caller_name="Dev Kapoor",
        emergency_flagged=0,
        case_summary="Asked for help debugging a Python script — reached the wrong business.",
        call_summary="Genuine caller with a software question; not a legal matter.",
        call_successful="False",
        user_sentiment="Positive",
        transcript=(
            "User: My Python script keeps crashing — can you help me fix it?\n"
            "Agent: I'm sorry, but that isn't something our law office handles. We only handle legal matters."
        ),
    )),
    ("out_of_scope_calls", dict(
        call_id="seed-oos-002",
        caller_name="Bea Lindqvist",
        emergency_flagged=0,
        case_summary="Asked about gym membership pricing; wrong number.",
        call_summary="Caller reached the wrong business entirely.",
        call_successful="False",
        user_sentiment="Neutral",
        transcript=(
            "User: How much is the monthly membership?\n"
            "Agent: I think you may have the wrong number — this is not the right office for that. We're a law office."
        ),
    )),
    ("emergency_flags", dict(
        call_id="seed-emergency-001",
        from_number="+15125550911",
        caller_name="Ray Delgado",
        emergency_flagged=1,
        case_summary="Reported an accident that had just happened with someone possibly hurt.",
        call_summary="Safety branch fired; caller told to hang up and call 911.",
        call_successful="False",
        user_sentiment="Negative",
        transcript=(
            "User: There's been an accident outside — someone's hurt right now.\n"
            "Agent: Your safety comes first. Please hang up and call 911 or your local emergency number immediately."
        ),
    )),
]

_STAFF = [
    ("Dana Cole", "attorney", "+15125550101", "101"),
    ("Marcus Webb", "attorney", "+15125550102", "102"),
    ("Priya Natarajan", "paralegal", "+15125550103", "103"),
    ("Rosa Jimenez", "billing", "+15125550104", "104"),
    ("Tom Delaney", "scheduling", "+15125550105", "105"),
]

# (bucket, call_id, assigned_to, court_status, next_hearing_date) — one case
# gets a hearing date, one gets a status with no date, one stays untouched so
# the "no status on file" path is testable.
_HANDLING = [
    ("cases", "seed-case-001", "Dana Cole",
     "Demand letter sent; awaiting insurer response", None),
    ("cases", "seed-case-002", "Marcus Webb",
     "Status conference scheduled", "2026-08-28"),
]


def seed_all() -> dict:
    """Populate every table with sample data. Safe to run repeatedly."""
    numbers: dict[str, list[str]] = {}
    for bucket, fields in _BUCKET_ROWS:
        db.upsert_record(bucket, _row(**fields))
        numbers.setdefault(bucket, []).append(
            db.get_record(bucket, fields["call_id"])["case_number"]
        )

    existing_names = {s["name"] for s in db.list_staff()}
    staff_created = 0
    for name, role, phone, ext in _STAFF:
        if name not in existing_names:
            db.create_staff(name, role, phone, ext)
            staff_created += 1
    staff_by_name = {s["name"]: s for s in db.list_staff()}

    for bucket, call_id, assigned_to, court_status, hearing in _HANDLING:
        db.set_case_assignment(bucket, call_id, assigned_to)
        if court_status or hearing:
            db.set_court_status(bucket, call_id, court_status, hearing)

    messages_created = 0
    if not db.list_messages(limit=1):
        case1 = db.get_record("cases", "seed-case-001")
        case2 = db.get_record("cases", "seed-case-002")
        for text, caller, phone, case_number, staff_name, delivered in [
            ("Wants to know if the insurer has responded to the demand letter.",
             "Maria Santos", "+15125559876", case1["case_number"], "Dana Cole", False),
            ("Asking what to bring to the status conference on the 28th.",
             "James Okafor", "+15125553402", case2["case_number"], "Marcus Webb", False),
            ("Question about the July invoice — thinks a consultation was billed twice.",
             "Sam Vale", "+15125557203", None, "Rosa Jimenez", True),
        ]:
            msg = db.create_message(
                message_text=text, caller_name=caller, callback_phone=phone,
                case_number=case_number,
                for_staff_id=staff_by_name[staff_name]["id"],
            )
            if delivered:
                db.mark_message_delivered(msg["id"], True)
            messages_created += 1

    return {
        "seeded": True,
        "case_numbers": numbers,
        "staff_created": staff_created,
        "messages_created": messages_created,
        "returning_caller_number": _RETURNING_NUMBER,
    }
