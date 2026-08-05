"""The intake field spec — one declaration of every fact the agent collects.

This is the single source of truth behind four things that used to drift
apart: the database columns, the row the webhook writes, the fields staff can
correct in the dashboard, and the Post-Call Data Extraction config pasted
into Retell. Add a field here and all four follow.

It mirrors the agent prompt directly. `CORE_FIELDS` is the prompt's Step 2
(asked on every call regardless of category) plus the flags the prompt sets
internally; `CATEGORY_FIELDS` is Step 3, one entry per category, and each
field's `must_ask` matches the prompt's own "Must ask" / "Ask if the
conversation allows" split. That split is what `missing_must_ask` measures —
the prompt's Step 4 completeness check, applied after the fact to the record
that actually landed.

Kept dependency-free so `db`, `webhooks`, `schemas`, and `main` can all import
it without a cycle.
"""
from dataclasses import dataclass

# The ten categories in the prompt's Step 1, in the prompt's own order.
CATEGORIES: list[tuple[str, str]] = [
    ("securities_fraud", "Securities Fraud"),
    ("shareholder_derivative", "Shareholder Derivative"),
    ("merger_transaction", "Merger / Transaction"),
    ("whistleblower_sec", "Whistleblower — SEC / CFTC"),
    ("whistleblower_qui_tam", "Whistleblower — Qui Tam"),
    ("whistleblower_retaliation", "Whistleblower Retaliation"),
    ("consumer_class", "Consumer Class"),
    ("data_privacy_class", "Data Privacy Class"),
    ("employment_class", "Employment Class"),
    ("other", "Other"),
]

CATEGORY_LABELS: dict[str, str] = dict(CATEGORIES)

# Categories where the caller is taking a personal risk by calling at all.
# The prompt hands these calls a confidentiality preamble, forbids pressing
# for documents or names, and bars ending the call for evasiveness.
WHISTLEBLOWER_CATEGORIES = frozenset(
    {"whistleblower_sec", "whistleblower_qui_tam", "whistleblower_retaliation"}
)


@dataclass(frozen=True)
class Field:
    """One intake fact.

    `kind` is "text" or "bool"; bools are stored as INTEGER and are
    three-state — 1, 0, or NULL for "never captured", which the prompt is
    explicit about treating as different from a "no".

    `description` is what gets pasted into Retell's Post-Call Data Extraction
    for this field, so it is written for the extraction model, not for staff.
    """

    name: str
    label: str
    kind: str
    description: str
    must_ask: bool = False


def _t(name: str, label: str, description: str, must_ask: bool = False) -> Field:
    return Field(name, label, "text", description, must_ask)


def _b(name: str, label: str, description: str, must_ask: bool = False) -> Field:
    return Field(name, label, "bool", description, must_ask)


# ------------------------------------------------------------- core --------
# Step 2 of the prompt, asked on every call whatever the category, plus the
# retention-agreement answer from Step 5 and the flags the prompt sets
# internally. `case_summary` is the one- or two-sentence summary in the
# caller's own words.
CORE_FIELDS: list[Field] = [
    _t("caller_name", "Caller name", "Full name of the caller, as spelled out on the call", True),
    _t("callback_phone", "Callback phone",
       "Best callback number, digits only, with country code if given", True),
    _t("email", "Email", "Caller's email address", True),
    _t("mailing_address", "Mailing address",
       "Best mailing address — city, state and ZIP at minimum", True),
    _t("case_summary", "Summary", "One or two sentence summary of the situation, in the caller's words", True),
    _b("represented_already", "Already represented",
       "True if the caller already has another attorney on this matter, or has "
       "already spoken with another firm about it", True),
    _t("other_firm_name", "Other firm",
       "Name of the other attorney or firm, if the caller is already represented "
       "or has spoken with one"),
    _t("prior_contact", "Prior contact",
       "Who has already contacted the caller or taken a statement about this — the "
       "company, its lawyers, an investigator, a government agency. \"no\" if none", True),
    _t("referral_source", "Referral source", "How the caller heard about the firm", True),
    _t("caller_affiliation", "Affiliation",
       "Whether the caller is currently an employee, officer, or director of the "
       "company involved (conflict check). \"none\" if they are not", True),
    _t("retention_consent", "Retention consent",
       "Whether the caller wants a retention agreement emailed if the attorney "
       "takes it on: yes, no, or undecided", True),
    _b("time_sensitive", "Time sensitive",
       "True if a lead plaintiff deadline, court notice, vote or tender date, "
       "filing deadline, or first-to-file whistleblower exposure came up"),
    _b("whistleblower_limited_disclosure", "Limited disclosure",
       "True if a whistleblower caller chose not to give details and only name, "
       "number, email, and employer or industry were taken"),
    _b("emergency_flagged", "Emergency flagged",
       "True only if the safety branch actually fired — the caller was told to "
       "hang up and call 911, or a whistleblower said they were in danger"),
    _t("additional_details", "Additional details",
       "Anything relevant that no other field covers"),
]

# Fields that exist for every category but are only asked in some of them, so
# they are listed by name in CATEGORY_FIELDS below rather than repeated.
_SHARED = {
    "opposing_party": _t("opposing_party", "Opposing party",
                         "The company, employer, agency, or acquirer the matter is against"),
    "key_date_or_deadline": _t("key_date_or_deadline", "Key date / deadline",
                               "Any vote, tender, closing, filing, or hearing date the caller mentioned"),
    "incident_date": _t("incident_date", "Incident date",
                        "Date of the adverse action or key event, YYYY-MM-DD if determinable"),
    "conduct_alleged": _t("conduct_alleged", "Conduct alleged",
                          "What the caller says was done wrong, in their own words"),
    "issuer_name": _t("issuer_name", "Company / issuer", "Name of the company whose securities are involved"),
    "ticker_symbol": _t("ticker_symbol", "Ticker", "Ticker symbol, letters only, as read back on the call"),
    "position_status": _t("position_status", "Position status",
                          "Whether the caller bought, sold, or still holds the securities"),
    "position_size": _t("position_size", "Position size",
                        "Roughly how many shares or units, or the total dollar amount invested"),
    "purchase_period": _t("purchase_period", "Purchase period",
                          "Roughly when the caller bought, and whether once or over a period"),
    "records_available": _b("records_available", "Has records",
                            "True if the caller has supporting records — statements, receipts, "
                            "pay stubs, the notice letter"),
    "still_employed": _b("still_employed", "Still employed",
                         "True if the caller still works for the employer involved"),
    "job_title": _t("job_title", "Job title", "The caller's role or job title"),
    "documentation_exists": _b("documentation_exists", "Has documentation",
                               "True if the caller says they have documents or records. Never ask "
                               "what they contain or where they are kept"),
    "others_affected": _b("others_affected", "Others affected",
                          "True if the caller believes other people were treated the same way"),
}


def _f(name: str, must_ask: bool = False) -> Field:
    """A shared field, at this category's must-ask level."""
    base = _SHARED[name]
    return base if base.must_ask == must_ask else Field(
        base.name, base.label, base.kind, base.description, must_ask
    )


# --------------------------------------------------------- per category ----
# Step 3 of the prompt. Order within each list is the order the prompt asks
# them in, and `must_ask` is the prompt's own "Must ask" vs "Ask if the
# conversation allows" split.
CATEGORY_FIELDS: dict[str, list[Field]] = {
    "securities_fraud": [
        _f("issuer_name", True),
        _f("ticker_symbol", True),
        _f("position_status", True),
        _f("purchase_period", True),
        _f("position_size", True),
        _b("still_holding", "Still holding", "True if the caller still holds any of the securities today", True),
        _t("triggering_event", "Triggering event",
           "What made the caller think something was wrong — a stock drop, a news "
           "story, an SEC filing, a law firm press release", True),
        _t("lead_plaintiff_deadline", "Lead plaintiff deadline",
           "The exact date on any notice or press release the caller mentioned", True),
        _f("records_available"),
        _t("brokerage_name", "Brokerage", "Which brokerage or platform the caller used"),
        _t("account_type", "Account type", "Whether the shares were held in a retirement or trust account"),
        _b("prior_lead_plaintiff", "Prior lead plaintiff",
           "True if the caller has served as a lead plaintiff or class representative before"),
    ],
    "shareholder_derivative": [
        _f("issuer_name", True),
        _f("ticker_symbol", True),
        _t("ownership_start", "Owned since", "Roughly when the caller acquired their shares", True),
        _b("continuous_ownership", "Continuous ownership",
           "True if the caller has held the shares continuously since then", True),
        _f("conduct_alleged", True),
        _t("information_source", "Information source", "How the caller learned about the conduct", True),
        _t("demand_status", "Demand status",
           "Whether a books-and-records or litigation demand has been sent, and any response"),
        _t("related_proceedings", "Related proceedings",
           "Any pending investigation, SEC action, or related lawsuit the caller knows of"),
    ],
    "merger_transaction": [
        _f("issuer_name", True),
        _f("opposing_party", True),
        _f("position_status", True),
        _f("key_date_or_deadline", True),
        _f("conduct_alleged", True),
        _f("position_size"),
        _f("ticker_symbol"),
        _t("vote_status", "Vote / tender status", "Whether the caller has already voted or tendered"),
    ],
    "whistleblower_sec": [
        _f("opposing_party", True),
        _f("conduct_alleged", True),
        _t("incident_period", "When it happened",
           "Roughly when the conduct happened, or whether it is still happening", True),
        _t("prior_report", "Already reported to",
           "Anyone the caller has already reported this to — SEC, CFTC, DOJ, an "
           "inspector general, an internal hotline, another law firm. \"no\" if none", True),
        _f("still_employed", True),
        _f("key_date_or_deadline", True),
        _f("job_title"),
        _f("documentation_exists"),
        _b("others_aware", "Others aware", "True if anyone else knows the caller is raising this"),
    ],
    # Qui tam asks exactly what the SEC/CFTC branch asks — the prompt runs
    # them off one shared list — so it shares the list here too rather than
    # keeping a second copy that could drift.
    "whistleblower_qui_tam": None,  # filled in below from whistleblower_sec
    "whistleblower_retaliation": [
        _f("opposing_party", True),
        _f("conduct_alleged", True),
        _t("reported_to", "Reported to", "Who the caller reported the underlying conduct to", True),
        _t("reported_date", "Reported on", "Roughly when the caller reported it", True),
        _t("adverse_action", "Adverse action",
           "What happened to the caller afterward — fired, demoted, suspended, "
           "hours cut, transferred", True),
        _f("incident_date", True),
        _f("still_employed", True),
        _f("job_title"),
        _t("employment_length", "Length of employment", "How long the caller worked there"),
        _f("documentation_exists"),
        _t("witnesses", "Witnesses", "Anyone who saw or knows about what happened"),
        _t("agency_filing", "Agency filing",
           "Whether the caller filed with OSHA, the EEOC, or a state agency, and when"),
    ],
    "consumer_class": [
        _f("opposing_party", True),
        _t("product_name", "Product / service", "The product or service involved", True),
        _f("conduct_alleged", True),
        _f("purchase_period", True),
        _t("purchase_channel", "Purchase channel",
           "Where it was bought — a store, a website, an app, a subscription", True),
        _t("amount_paid", "Amount paid", "Roughly how much the caller paid or was charged", True),
        _f("records_available", True),
        _t("purchase_state", "Purchase state",
           "The state the caller bought it in or was living in at the time", True),
        _t("company_contacted", "Contacted the company",
           "Whether the caller contacted the company about it, and what happened"),
        _f("others_affected"),
        _b("physical_injury", "Physical injury",
           "True if the caller was physically harmed by the product. Flag for "
           "attorney review; do not pursue injury details"),
    ],
    "data_privacy_class": [
        _f("opposing_party", True),
        _b("notice_received", "Breach notice received",
           "True if the caller received a breach notice letter or email", True),
        _t("notice_date", "Notice date", "The date on the breach notice", True),
        _t("data_types_involved", "Data involved",
           "Kinds of information involved — name, Social Security number, financial "
           "account, medical, biometric. Never record an actual account or SSN", True),
        _t("harm_experienced", "Harm experienced",
           "Any actual misuse seen — fraudulent charges, accounts opened, tax "
           "filings, identity theft", True),
        _t("residence_state", "State of residence", "What state the caller lives in", True),
        _t("relationship_type", "Relationship",
           "Whether the caller was a customer, patient, employee, or user, and roughly when"),
        _t("out_of_pocket_costs", "Out of pocket",
           "Whether the caller paid for credit monitoring or spent time dealing with it"),
        _f("records_available"),
    ],
    "employment_class": [
        _f("opposing_party", True),
        _f("job_title", True),
        _t("pay_type", "Pay type", "Whether the caller was paid hourly or salaried", True),
        _f("conduct_alleged", True),
        _t("employment_period", "Employment period", "Roughly what dates the caller worked there", True),
        _f("still_employed", True),
        _t("work_state", "Work state", "Which state the caller worked in", True),
        _f("others_affected", True),
        _t("hours_worked", "Hours worked", "Roughly how many hours a week the caller worked"),
        _f("records_available"),
        _b("arbitration_agreement", "Arbitration agreement",
           "True if the caller signed an arbitration agreement or class waiver"),
        _b("reported_internally", "Raised internally",
           "True if the caller raised it with HR or a supervisor"),
    ],
    # Open-ended by design. The prompt still requires the opposing party, an
    # approximate date, and whether others were affected the same way.
    "other": [
        _f("opposing_party", True),
        _f("incident_date", True),
        _f("others_affected", True),
        _f("conduct_alleged"),
    ],
}

CATEGORY_FIELDS["whistleblower_qui_tam"] = CATEGORY_FIELDS["whistleblower_sec"]

# Every category the prompt defines must have a field list, or its calls
# silently record only the core fields — which is exactly how qui_tam
# arrived with nine missing questions and a clean completeness check.
assert set(CATEGORY_FIELDS) == {c for c, _ in CATEGORIES}, (
    "every category in CATEGORIES needs an entry in CATEGORY_FIELDS"
)


# ----------------------------------------------------------- derived -------

def _dedupe(fields: list[Field]) -> list[Field]:
    """First mention of each name wins, preserving order."""
    seen: set[str] = set()
    out: list[Field] = []
    for f in fields:
        if f.name not in seen:
            seen.add(f.name)
            out.append(f)
    return out


# Every field, core first then each category's in prompt order. A field used
# by several categories appears once, at its first mention.
ALL_FIELDS: list[Field] = _dedupe(
    CORE_FIELDS + [f for fields in CATEGORY_FIELDS.values() for f in fields]
)

FIELDS_BY_NAME: dict[str, Field] = {f.name: f for f in ALL_FIELDS}

BOOL_FIELDS: frozenset[str] = frozenset(f.name for f in ALL_FIELDS if f.kind == "bool")

# Column name -> SQLite type, for the schema and the migration in db.py.
COLUMNS: list[tuple[str, str]] = [
    (f.name, "INTEGER" if f.kind == "bool" else "TEXT") for f in ALL_FIELDS
]

# Columns that make a call a usable case. Deliberately not the whole must-ask
# list: a caller who gave their name, a number, a category, and what happened
# is someone an attorney can act on, and holding that call out of the queue
# because the ticker was never caught would help nobody. The rest of the
# must-ask list is reported per record by missing_must_ask() instead.
REQUIRED_FOR_CASE = ("caller_name", "callback_phone", "case_category", "case_summary")


def fields_for(category: str | None) -> list[Field]:
    """Core fields plus the ones this category actually asks about, in the
    order the prompt asks them. Unknown categories get the core set only."""
    return _dedupe(CORE_FIELDS + CATEGORY_FIELDS.get(category or "", []))


def must_ask_for(category: str | None) -> list[str]:
    """Field names the prompt requires before closing, for this category."""
    return [f.name for f in fields_for(category) if f.must_ask]


def _captured(record: dict, name: str) -> bool:
    """Did this field actually come back with something?

    "unknown" counts as captured: the prompt tells the agent to record an
    unanswered question that way, and asked-and-unknown is a real answer. A
    NULL is what "never asked" looks like, and that is what this reports.
    """
    value = record.get(name)
    if value is None:
        return False
    return str(value).strip() != ""


def missing_must_ask(record: dict) -> list[str]:
    """Must-ask fields this record never captured — the prompt's own Step 4
    check, run against what actually landed. Empty means a complete intake."""
    category = record.get("case_category")
    return [name for name in must_ask_for(category) if not _captured(record, name)]


def field_view(record: dict) -> list[dict]:
    """This record's intake fields with their labels and values, for the
    dashboard — so the ~60 labels live here rather than being duplicated in
    the frontend, and a new field shows up without a frontend change."""
    return [
        {
            "name": f.name,
            "label": f.label,
            "kind": f.kind,
            "must_ask": f.must_ask,
            "value": record.get(f.name),
        }
        for f in fields_for(record.get("case_category"))
    ]
