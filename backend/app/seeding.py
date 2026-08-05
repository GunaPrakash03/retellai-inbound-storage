"""Sample data for every table, used by POST /debug/seed (gated behind
DEBUG_ENDPOINTS=1 in main.py).

The bucket records are shaped exactly like the webhook handler writes them —
full column set, transcripts that end with the agent's scripted closing
lines — so everything downstream (outcome detection, caller history, the
dashboard, case lookup) behaves as it would with real calls.

There is exactly one completed case per practice area, each with its
matter type set, plus one representative call in each of the other buckets
(emergency, partial, spam, unwanted, out of scope) so no dashboard view is
empty in a demo.

Idempotent: bucket rows upsert on fixed call_ids and keep their case
numbers; staff are matched by name; messages are only created while the
table is empty. Pass reset=True to seed_all to wipe existing call data
first — see db.reset_call_data.
"""
import uuid

from . import db

# A returning caller: the securities case and a later dropped call share this
# number, so the inbound webhook greets them as a known caller.
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
        "Agent: Thank you, I have everything I need. Someone from our team will "
        "review this and follow up with you soon. Take care."
    )


# Answers every completed intake carries, whatever the category — the prompt's
# Step 2 plus the Step 5 retention question. Spelled out once here so each
# case below only has to state what makes it that category.
_CORE = dict(
    represented_already=0,
    prior_contact="no",
    referral_source="Google search",
    caller_affiliation="none",
    retention_consent="yes",
    call_successful="True",
)


# One completed case per practice area, keyed by a stable call_id so
# re-seeding keeps each case's number. Every case carries a matter type and
# the must-ask fields its category calls for.
_CATEGORY_CASES: list[dict] = [
    dict(
        _CORE,
        call_id="seed-securities_fraud",
        from_number=_RETURNING_NUMBER,
        case_category="securities_fraud",
        case_subcategory="stock_drop_after_disclosure",
        caller_name="Nathan Brooks",
        callback_phone="+15125559876",
        is_phone_valid=1,
        email="nathan.brooks@example.com",
        is_email_valid=1,
        mailing_address="118 Elm Ridge Dr, Round Rock, TX 78664",
        issuer_name="Meridian Therapeutics",
        ticker_symbol="MRDT",
        position_status="bought and still holds",
        purchase_period="Bought in three lots between March and June 2026",
        position_size="About 4,000 shares, roughly $52,000",
        still_holding=1,
        triggering_event="Stock fell 38% the morning after the FDA rejected their lead candidate; a press release said the company had known about the trial data for months.",
        lead_plaintiff_deadline="2026-09-08",
        records_available=1,
        brokerage_name="Fidelity",
        account_type="Individual taxable",
        prior_lead_plaintiff=0,
        time_sensitive=1,
        key_date_or_deadline="2026-09-08",
        opposing_party="Meridian Therapeutics",
        case_summary="Bought Meridian Therapeutics shares before an FDA rejection wiped out a third of the value; a law firm notice mentions a September lead plaintiff deadline.",
        call_summary="Completed securities fraud intake with a lead plaintiff deadline in five weeks.",
        user_sentiment="Neutral",
        transcript=_transcript(
            "I lost a lot on Meridian Therapeutics and I saw a notice about a deadline next month.",
            "I understand, let me take down the details so an attorney can review it.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-shareholder_derivative",
        case_category="shareholder_derivative",
        case_subcategory="self_dealing",
        caller_name="Deborah Klein",
        callback_phone="+15125550210",
        is_phone_valid=1,
        email="d.klein@example.com",
        is_email_valid=1,
        mailing_address="2204 Wexford Ln, Austin, TX 78745",
        issuer_name="Calder Industrial Group",
        ticker_symbol="CALD",
        ownership_start="2019",
        continuous_ownership=1,
        conduct_alleged="Two directors approved a supply contract with a company owned by the CEO's brother-in-law, at what she believes are well above market rates.",
        information_source="A Wall Street Journal story, then the company's own proxy statement",
        demand_status="No demand sent yet",
        related_proceedings="None that she knows of",
        opposing_party="Calder Industrial Group board",
        case_summary="Long-time shareholder raising a related-party supply contract approved by the board, disclosed in the proxy after a press report.",
        call_summary="Completed derivative intake over a related-party transaction.",
        user_sentiment="Negative",
        transcript=_transcript(
            "I've held Calder stock since 2019 and the board approved a contract with the CEO's relative.",
            "Understood, let me get the details for the attorney to review.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-merger_transaction",
        case_category="merger_transaction",
        case_subcategory="take_private",
        caller_name="Raymond Getty",
        callback_phone="+15125550282",
        is_phone_valid=1,
        email="ray.getty@example.com",
        is_email_valid=1,
        mailing_address="905 Sabine St, Austin, TX 78701",
        issuer_name="Harborline Systems",
        ticker_symbol="HRBL",
        opposing_party="Vantry Capital Partners (acquirer)",
        position_status="Held at announcement and still holds",
        position_size="About 12,000 shares",
        vote_status="Has not voted yet",
        key_date_or_deadline="2026-08-27",
        conduct_alleged="Believes the $19 per share price is well below what the company is worth, and that the proxy left out the banker's conflicts.",
        time_sensitive=1,
        case_summary="Shareholder objecting to a take-private at $19 a share, with the vote scheduled for late August and disclosure concerns about the proxy.",
        call_summary="Completed merger intake ahead of a shareholder vote in three weeks.",
        user_sentiment="Negative",
        transcript=_transcript(
            "They're taking Harborline private at nineteen dollars and the vote is at the end of the month.",
            "Thanks, let me capture the details before the attorney calls you.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-whistleblower_sec",
        case_category="whistleblower_sec",
        case_subcategory="accounting_fraud",
        caller_name="Alan Reyes",
        callback_phone="+15125550311",
        is_phone_valid=1,
        email="a.reyes@example.com",
        is_email_valid=1,
        mailing_address="Prefers not to give one; email is best",
        opposing_party="Northgate Payments Inc.",
        conduct_alleged="Revenue from multi-year contracts is being recognized up front to hit quarterly targets; he raised it internally twice.",
        incident_period="Since roughly Q3 2025, still happening",
        prior_report="Internal compliance hotline only",
        still_employed=1,
        job_title="Senior revenue accountant",
        documentation_exists=1,
        others_aware=0,
        key_date_or_deadline="unknown",
        time_sensitive=1,
        retention_consent="undecided",
        referral_source="A colleague who used the firm",
        case_summary="Revenue accountant reporting front-loaded revenue recognition at his employer; raised internally, not yet reported to the SEC.",
        call_summary="Completed SEC whistleblower intake; caller still employed and has not filed anywhere.",
        user_sentiment="Neutral",
        transcript=_transcript(
            "I work in accounting and we're booking revenue we haven't earned yet. I'd rather not say too much.",
            "That's completely fine, and this call is confidential. Let me get just enough for an attorney to call you back.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-whistleblower_qui_tam",
        case_category="whistleblower_qui_tam",
        case_subcategory="medicare_medicaid_fraud",
        caller_name="Sofia Marchetti",
        callback_phone="+15125550233",
        is_phone_valid=1,
        email="sofia.m@example.com",
        is_email_valid=1,
        mailing_address="77 Anderson Mill Rd, Cedar Park, TX 78613",
        opposing_party="Hill Country Home Health",
        conduct_alleged="Visits billed to Medicare that never took place, and patients kept on service after they no longer qualified.",
        incident_period="Roughly the last two years, still happening",
        prior_report="no",
        still_employed=1,
        job_title="Scheduling coordinator",
        documentation_exists=1,
        others_aware=1,
        key_date_or_deadline="unknown",
        time_sensitive=1,
        case_summary="Home health scheduler describing billed visits that never happened and patients kept on service past eligibility. Not reported anywhere yet.",
        call_summary="Completed qui tam intake; first-to-file exposure flagged.",
        user_sentiment="Negative",
        transcript=_transcript(
            "They're billing Medicare for visits that never happened and I have the schedules.",
            "Thank you for telling me. This call is confidential and you don't need to give me any documents right now.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-whistleblower_retaliation",
        case_category="whistleblower_retaliation",
        case_subcategory="termination",
        caller_name="Marcus Feldman",
        callback_phone="+15125550247",
        is_phone_valid=1,
        email="marcus.feldman@example.com",
        is_email_valid=1,
        mailing_address="3390 Pecan Grove Way, Pflugerville, TX 78660",
        opposing_party="Brightpath Logistics",
        conduct_alleged="Reported that quarterly freight revenue was being pulled forward into the prior period.",
        reported_to="His VP of finance, then the audit committee",
        reported_date="2026-05-04",
        adverse_action="Fired, told it was a restructuring",
        incident_date="2026-07-15",
        still_employed=0,
        job_title="Financial controller",
        employment_length="Six years",
        documentation_exists=1,
        witnesses="Two people on his team were in the meeting",
        agency_filing="Nothing filed yet",
        time_sensitive=1,
        case_summary="Controller fired ten weeks after reporting pulled-forward revenue to the audit committee; termination described as a restructuring.",
        call_summary="Completed retaliation intake; adverse action date recorded for the filing clock.",
        user_sentiment="Negative",
        transcript=_transcript(
            "I reported the revenue numbers to the audit committee in May and they let me go in July.",
            "I'm sorry that happened. Let me take the dates down carefully.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-consumer_class",
        case_category="consumer_class",
        case_subcategory="auto_renewal_subscription",
        caller_name="Priscilla Alvarez",
        callback_phone="+15125550274",
        is_phone_valid=1,
        email="priscilla.alvarez@example.com",
        is_email_valid=1,
        mailing_address="1420 Barton Springs Rd, Austin, TX 78704",
        opposing_party="Lumen Fitness App",
        product_name="Lumen Premium annual subscription",
        conduct_alleged="A free trial rolled into a $179 annual plan with no reminder, and the cancel button leads to a page that never loads.",
        purchase_period="Signed up in January 2026, charged in February",
        purchase_channel="iPhone app",
        amount_paid="$179, charged twice",
        records_available=1,
        purchase_state="TX",
        company_contacted="Emailed support twice, no reply",
        others_affected=1,
        physical_injury=0,
        case_summary="Charged twice for an annual subscription after a free trial auto-renewed, with no working way to cancel in the app.",
        call_summary="Completed consumer intake over an auto-renewal and double charge.",
        user_sentiment="Negative",
        transcript=_transcript(
            "This app charged me a hundred and seventy nine dollars twice and I can't cancel it.",
            "Let's get the details down so an attorney can look at it.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-data_privacy_class",
        case_category="data_privacy_class",
        case_subcategory="data_breach",
        caller_name="Helen Watanabe",
        callback_phone="+15125550291",
        is_phone_valid=1,
        email="helen.watanabe@example.com",
        is_email_valid=1,
        mailing_address="612 Rivery Blvd, Georgetown, TX 78628",
        opposing_party="Sentinel Medical Billing",
        notice_received=1,
        notice_date="2026-06-19",
        data_types_involved="Name, date of birth, Social Security number, and medical billing records",
        harm_experienced="Two credit card accounts opened in her name in July",
        residence_state="TX",
        relationship_type="Patient, billed through them since 2023",
        out_of_pocket_costs="Paying $24 a month for credit monitoring",
        records_available=1,
        incident_date="2026-06-19",
        case_summary="Received a breach notice from a medical billing vendor, then found two credit cards opened in her name the following month.",
        call_summary="Completed data privacy intake with actual downstream identity theft.",
        user_sentiment="Negative",
        transcript=_transcript(
            "I got a breach letter from my medical biller and now there are credit cards in my name.",
            "I'm sorry, that's a lot to deal with. Let me take the details down.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-employment_class",
        case_category="employment_class",
        case_subcategory="off_the_clock_work",
        caller_name="Tyler Nguyen",
        callback_phone="+15125550258",
        is_phone_valid=1,
        email="tyler.nguyen@example.com",
        is_email_valid=1,
        mailing_address="8801 Research Blvd, Austin, TX 78758",
        opposing_party="Vertex Fulfillment Services",
        job_title="Warehouse team lead",
        pay_type="Hourly",
        conduct_alleged="Required to be on site 20 minutes before clocking in for a security screening and shift huddle, unpaid.",
        employment_period="March 2024 to present",
        still_employed=1,
        work_state="TX",
        others_affected=1,
        hours_worked="About 45 a week",
        records_available=1,
        arbitration_agreement=1,
        reported_internally=1,
        case_summary="Warehouse lead describing 20 minutes of unpaid pre-shift screening and huddle time, applied across his whole shift.",
        call_summary="Completed employment class intake over off-the-clock pre-shift work.",
        user_sentiment="Neutral",
        transcript=_transcript(
            "We have to be there twenty minutes early for screening and we don't get paid for it.",
            "Got it, let me take down the details so an attorney can review this.",
        ),
    ),
    dict(
        _CORE,
        call_id="seed-other",
        case_category="other",
        caller_name="Curtis Bell",
        callback_phone="+15125550303",
        is_phone_valid=1,
        email="curtis.bell@example.com",
        is_email_valid=1,
        mailing_address="204 W 9th St, Austin, TX 78701",
        opposing_party="Ridgeline Credit Union",
        incident_date="2026-04-02",
        others_affected=1,
        conduct_alleged="Overdraft fees charged on transactions that showed an available balance at the time they were authorized.",
        case_summary="Overdraft fees charged against balances that appeared available when the transactions were authorized; thinks it affects other members too.",
        additional_details="Doesn't fit a standard consumer product claim; wants an attorney to say whether the fee practice is worth looking at.",
        call_summary="Completed intake logged under Other for a bank fee practice.",
        user_sentiment="Neutral",
        transcript=_transcript(
            "My credit union charges overdraft fees even when the app showed the money was there.",
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
        case_summary="Said someone was breaking into the house while he was on the line.",
        call_summary="Safety branch fired; caller told to hang up and call 911.",
        call_successful="False",
        user_sentiment="Negative",
        transcript=(
            "User: Someone is trying to get in the house right now.\n"
            "Agent: Please hang up and call 911 right now."
        ),
    )),
    ("partial_calls", dict(
        call_id="seed-partial",
        from_number=_RETURNING_NUMBER,
        case_category="securities_fraud",
        caller_name="Nathan Brooks",
        case_summary="Called back about the Meridian shares; call dropped before finishing.",
        call_summary="Caller disconnected mid-conversation.",
        call_successful="False",
        user_sentiment="Neutral",
        transcript=(
            "User: Hi, I called before about my Meridian shares —\n"
            "Agent: It looks like we may have gotten disconnected, or you're not able "
            "to hear me right now. I'll go ahead and end this call here, please call "
            "us back whenever works for you."
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
            "Agent: I want to make sure I'm getting accurate information for the "
            "attorney, and I'm having a hard time following the details. Let's stop "
            "here for now, please feel free to call us back when you're able to go "
            "through this with us."
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
            "Agent: It sounds like now might not be the right time to go through "
            "these details, feel free to call us back when you're ready to share "
            "what's going on."
        ),
    )),
    ("out_of_scope_calls", dict(
        call_id="seed-out-of-scope",
        caller_name="Dev Kapoor",
        case_summary="Asked for help with a divorce filing — outside the firm's practice areas.",
        call_summary="Genuine legal question, but not shareholder, whistleblower, or consumer work.",
        call_successful="False",
        user_sentiment="Positive",
        transcript=(
            "User: I need help filing for a divorce.\n"
            "Agent: That's outside what our firm handles, we focus on shareholder, "
            "whistleblower, and consumer cases. I'd suggest contacting your state or "
            "local bar association's referral service. I'm sorry we're not the right "
            "place for this one. Take care."
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
    ("seed-securities_fraud", "Dana Cole",
     "Lead plaintiff motion being prepared", "2026-09-08", "Dana Cole"),
    ("seed-merger_transaction", "Marcus Webb",
     "Expedited disclosure motion filed ahead of the vote", "2026-08-27", "Marcus Webb"),
    ("seed-whistleblower_retaliation", "Marcus Webb",
     "OSHA complaint drafted; not yet filed", None, None),
    ("seed-consumer_class", "Dana Cole",
     "Demand letter sent; awaiting the company's response", "2026-09-22", "Priya Natarajan"),
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
        securities = db.get_record("cases", "seed-securities_fraud")
        merger = db.get_record("cases", "seed-merger_transaction")
        for text, caller, phone, case_number, staff_name, delivered in [
            ("Wants to know whether the lead plaintiff motion was filed before the deadline.",
             "Nathan Brooks", "+15125559876", securities["case_number"], "Dana Cole", False),
            ("Asking whether he should vote his shares before the meeting.",
             "Raymond Getty", "+15125550282", merger["case_number"], "Marcus Webb", False),
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
