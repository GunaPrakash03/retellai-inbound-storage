"""Sample data for every table, used by POST /debug/seed (gated behind
DEBUG_ENDPOINTS=1 in main.py).

The bucket records are shaped exactly like the webhook handler writes them —
full column set, transcripts that end with the agent's scripted closing
lines — so everything downstream (outcome detection, caller history, the
dashboard, case lookup) behaves as it would with real calls.

There is exactly one completed case per legal category, each with its
subcategory set, plus one representative call in each of the other buckets
(emergency, partial, spam, unwanted, out of scope) so no dashboard view is
empty in a demo.

Idempotent: bucket rows upsert on fixed call_ids and keep their case
numbers; staff are matched by name; messages are only created while the
table is empty. Pass reset=True to seed_all to wipe existing call data
first — see db.reset_call_data.
"""
import uuid

from . import db

# A returning caller: the personal-injury case and a later dropped call share
# this number, so the inbound webhook greets them as a known caller.
_RETURNING_NUMBER = "+15125559876"


def _row(call_id: str, **overrides) -> dict:
    """A full webhook-shaped row: every updatable column present."""
    row = {c: None for c in db._UPDATABLE_COLUMNS}
    row.update({"id": str(uuid.uuid4()), "call_id": call_id})
    row.update(overrides)
    return row


def _transcript(user_line: str, agent_line: str) -> str:
    """A short intake transcript ending on the agent's scripted completed
    line, so transcript-based outcome detection files it as a finished case."""
    return (
        f"User: {user_line}\n"
        f"Agent: {agent_line}\n"
        "Agent: Thank you. I have everything I need to pass along to our attorneys."
    )


# One completed case per category, keyed by a stable call_id so re-seeding
# keeps each case's number. Every case carries a subcategory.
_CATEGORY_CASES: list[dict] = [
    dict(
        call_id="seed-personal_injury",
        from_number=_RETURNING_NUMBER,
        case_category="personal_injury",
        case_subcategory="car_accident",
        caller_name="Nathan Brooks",
        callback_phone="+15125559876",
        is_phone_valid=1,
        email="nathan.brooks@example.com",
        is_email_valid=1,
        incident_date="2026-07-22",
        location="Round Rock, TX",
        opposing_party="Delivery van driver",
        represented_already=0,
        injured=1,
        police_report_filed=1,
        case_summary="Rear-ended at a red light by a delivery van; neck and shoulder pain, treated at urgent care.",
        call_summary="Completed intake for a rear-end collision with injuries.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=_transcript(
            "I was rear-ended at a light last week and my neck still hurts.",
            "I'm sorry to hear that — let me take down the details.",
        ),
    ),
    dict(
        call_id="seed-workplace_employment",
        case_category="workplace_employment",
        case_subcategory="wrongful_termination",
        caller_name="Deborah Klein",
        callback_phone="+15125550210",
        is_phone_valid=1,
        email="d.klein@example.com",
        is_email_valid=1,
        incident_date="2026-07-15",
        location="Austin, TX",
        opposing_party="Brightpath Logistics (former employer)",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="Fired two weeks after reporting a safety violation to her supervisor; believes it was retaliation.",
        call_summary="Completed intake for a possible retaliatory termination.",
        call_successful="True",
        user_sentiment="Negative",
        transcript=_transcript(
            "I got let go right after I reported a safety problem at work.",
            "Understood — let me get the details for the attorney to review.",
        ),
    ),
    dict(
        call_id="seed-medical_product",
        case_category="medical_product",
        case_subcategory="medical_malpractice",
        caller_name="Sofia Marchetti",
        callback_phone="+15125550233",
        is_phone_valid=1,
        email="sofia.m@example.com",
        is_email_valid=1,
        incident_date="2026-06-30",
        location="Cedar Park, TX",
        opposing_party="Hill Country Surgical Center",
        represented_already=0,
        injured=1,
        police_report_filed=0,
        case_summary="Complications after a routine procedure; a surgical sponge was left behind and required a second surgery.",
        call_summary="Completed intake for a possible surgical-error malpractice claim.",
        call_successful="True",
        user_sentiment="Negative",
        transcript=_transcript(
            "They left something inside me after surgery and I had to be opened up again.",
            "I'm so sorry — let me take down what happened.",
        ),
    ),
    dict(
        call_id="seed-family_law",
        case_category="family_law",
        case_subcategory="divorce",
        caller_name="Marcus Feldman",
        callback_phone="+15125550247",
        is_phone_valid=1,
        email="marcus.feldman@example.com",
        is_email_valid=1,
        location="Pflugerville, TX",
        opposing_party="Spouse",
        key_date_or_deadline="2026-09-15",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="Wants to file for divorce; two minor children and a jointly owned home involved.",
        call_summary="Completed intake for a divorce with children and shared property.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=_transcript(
            "My spouse and I are separating and we have two kids and a house together.",
            "Thanks for sharing that — a few questions so the right attorney can review it.",
        ),
    ),
    dict(
        call_id="seed-criminal_defense",
        case_category="criminal_defense",
        case_subcategory="dui_dwi",
        caller_name="Tyler Nguyen",
        callback_phone="+15125550258",
        is_phone_valid=1,
        email="tyler.nguyen@example.com",
        is_email_valid=1,
        incident_date="2026-07-27",
        location="Austin, TX",
        key_date_or_deadline="2026-08-19",
        represented_already=0,
        injured=0,
        police_report_filed=1,
        case_summary="Arrested for DUI over the weekend; arraignment scheduled and needs representation.",
        call_summary="Completed intake for a DUI arrest with an upcoming arraignment.",
        call_successful="True",
        user_sentiment="Negative",
        transcript=_transcript(
            "I got arrested for a DUI this weekend and I have a court date coming up.",
            "Okay — let me get the details so an attorney can follow up quickly.",
        ),
    ),
    dict(
        call_id="seed-immigration",
        case_category="immigration",
        case_subcategory="green_card",
        caller_name="Amara Okonkwo",
        callback_phone="+15125550266",
        is_phone_valid=1,
        email="amara.o@example.com",
        is_email_valid=1,
        location="Austin, TX",
        key_date_or_deadline="2026-10-01",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="Applying for a green card through marriage; wants help preparing the adjustment-of-status filing.",
        call_summary="Completed intake for a marriage-based green card application.",
        call_successful="True",
        user_sentiment="Positive",
        transcript=_transcript(
            "I'm trying to get my green card through my marriage and need help with the paperwork.",
            "Happy to help get you to the right attorney — let me take some details.",
        ),
    ),
    dict(
        call_id="seed-real_estate_housing",
        case_category="real_estate_housing",
        case_subcategory="eviction",
        caller_name="Priscilla Alvarez",
        callback_phone="+15125550274",
        is_phone_valid=1,
        email="priscilla.alvarez@example.com",
        is_email_valid=1,
        location="1420 Barton Springs Rd, Austin, TX",
        opposing_party="Landlord — Cypress Property Mgmt",
        key_date_or_deadline="2026-08-11",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="Served an eviction notice she believes is retaliatory after requesting repairs; hearing in under two weeks.",
        call_summary="Completed intake for a contested eviction with a near-term hearing.",
        call_successful="True",
        user_sentiment="Negative",
        transcript=_transcript(
            "My landlord is trying to evict me after I asked them to fix the heating.",
            "Let's get the details down so an attorney can look at this right away.",
        ),
    ),
    dict(
        call_id="seed-business_contract",
        case_category="business_contract",
        case_subcategory="breach_of_contract",
        caller_name="Raymond Getty",
        callback_phone="+15125550282",
        is_phone_valid=1,
        email="ray@gettyfabrication.example.com",
        is_email_valid=1,
        incident_date="2026-05-20",
        location="Austin, TX",
        opposing_party="Marlow Interiors LLC",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="A client refuses to pay the final invoice on a signed fabrication contract; dispute over delivered scope.",
        call_summary="Completed intake for an unpaid-invoice contract dispute.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=_transcript(
            "A client signed a contract and now won't pay the last invoice.",
            "Understood — let me capture the details of the agreement.",
        ),
    ),
    dict(
        call_id="seed-estate_disability",
        case_category="estate_disability",
        case_subcategory="probate",
        caller_name="Helen Watanabe",
        callback_phone="+15125550291",
        is_phone_valid=1,
        email="helen.watanabe@example.com",
        is_email_valid=1,
        incident_date="2026-06-10",
        location="Georgetown, TX",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="Her father passed away and left a will; needs help opening probate and settling the estate.",
        call_summary="Completed intake for a probate matter following a parent's death.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=_transcript(
            "My father passed away and left a will, and I need help with probate.",
            "I'm sorry for your loss — let me take down the details.",
        ),
    ),
    dict(
        call_id="seed-other",
        case_category="other",
        caller_name="Curtis Bell",
        callback_phone="+15125550303",
        is_phone_valid=1,
        email="curtis.bell@example.com",
        is_email_valid=1,
        location="Austin, TX",
        represented_already=0,
        injured=0,
        police_report_filed=0,
        case_summary="A neighbor dispute over a shared fence and property line that doesn't fit the usual categories.",
        additional_details="Wants to understand options before deciding whether it's worth pursuing.",
        call_summary="Completed intake for a boundary dispute logged under Other.",
        call_successful="True",
        user_sentiment="Neutral",
        transcript=_transcript(
            "My neighbor and I disagree about where the property line is and who owns the fence.",
            "Let me take the details so the right attorney can weigh in.",
        ),
    ),
]

# One representative call in each non-case bucket, so those views aren't
# empty in a demo. These mirror how the webhook routes real calls by their
# scripted closing lines.
_OTHER_BUCKET_ROWS: list[tuple[str, dict]] = [
    ("emergency_flags", dict(
        call_id="seed-emergency",
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
    ("partial_calls", dict(
        call_id="seed-partial",
        from_number=_RETURNING_NUMBER,
        case_category="personal_injury",
        caller_name="Nathan Brooks",
        case_summary="Called back about the collision case; call dropped before finishing.",
        call_summary="Caller disconnected mid-conversation.",
        call_successful="False",
        user_sentiment="Neutral",
        transcript=(
            "User: Hi, I called before about my accident —\n"
            "Agent: It looks like we may have gotten disconnected. If you can hear me, please call back anytime."
        ),
    )),
    ("unwanted_calls", dict(
        call_id="seed-unwanted",
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
        call_id="seed-spam",
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
        call_id="seed-out-of-scope",
        caller_name="Dev Kapoor",
        case_summary="Asked for help debugging a script — reached the wrong business.",
        call_summary="Genuine caller with a software question; not a legal matter.",
        call_successful="False",
        user_sentiment="Positive",
        transcript=(
            "User: My script keeps crashing — can you help me fix it?\n"
            "Agent: I'm sorry, but that isn't something our law office handles. We only handle legal matters."
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

# (call_id, assigned_to, court_status, next_hearing_date, hearing_attorney).
# A few cases get handling so the assignment and court-status features have
# something to show; the eviction's hearing attorney differs from the
# assigned attorney, exercising the coverage split.
_HANDLING = [
    ("seed-personal_injury", "Dana Cole",
     "Demand letter sent; awaiting insurer response", None, None),
    ("seed-family_law", "Marcus Webb",
     "Temporary orders hearing scheduled", "2026-09-15", "Marcus Webb"),
    ("seed-real_estate_housing", "Dana Cole",
     "Answer filed; contested-eviction hearing set", "2026-08-11", "Priya Natarajan"),
    ("seed-criminal_defense", "Marcus Webb",
     "Arraignment upcoming; reviewing the police report", "2026-08-19", "Marcus Webb"),
]


def seed_all(reset: bool = False) -> dict:
    """Populate every table with sample data. Safe to run repeatedly.

    With reset=True, wipes all existing call data first (see
    db.reset_call_data), leaving exactly the sample set below.
    """
    cleared = db.reset_call_data() if reset else None

    numbers: dict[str, list[str]] = {}
    for fields in _CATEGORY_CASES:
        db.upsert_record("cases", _row(**fields))
        numbers.setdefault("cases", []).append(
            db.get_record("cases", fields["call_id"])["case_number"]
        )
    for bucket, fields in _OTHER_BUCKET_ROWS:
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

    for call_id, assigned_to, court_status, hearing, hearing_attorney in _HANDLING:
        db.set_case_assignment("cases", call_id, assigned_to)
        if court_status or hearing or hearing_attorney:
            db.set_court_status("cases", call_id, court_status, hearing, hearing_attorney)

    messages_created = 0
    if not db.list_messages(limit=1):
        injury = db.get_record("cases", "seed-personal_injury")
        family = db.get_record("cases", "seed-family_law")
        for text, caller, phone, case_number, staff_name, delivered in [
            ("Wants to know if the insurer has responded to the demand letter.",
             "Nathan Brooks", "+15125559876", injury["case_number"], "Dana Cole", False),
            ("Asking what to bring to the temporary orders hearing.",
             "Marcus Feldman", "+15125550247", family["case_number"], "Marcus Webb", False),
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
        "reset": reset,
        "cleared": cleared,
        "case_numbers": numbers,
        "staff_created": staff_created,
        "messages_created": messages_created,
        "returning_caller_number": _RETURNING_NUMBER,
    }
