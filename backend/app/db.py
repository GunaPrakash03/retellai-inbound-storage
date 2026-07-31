import os
import secrets
import sqlite3
import uuid
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "./data/cases.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# Every call bucket is stored in its own table with this identical shape, so
# a call can only ever land in one bucket: completed intakes, calls that
# dropped early, nonsensical/prank calls, evasive callers, people who
# reached the wrong business, and safety escalations.
BUCKETS = [
    "cases",
    "partial_calls",
    "unwanted_calls",
    "spam_calls",
    "out_of_scope_calls",
    "emergency_flags",
]

_TABLE_TEMPLATE = """
CREATE TABLE IF NOT EXISTS {table} (
    id                    TEXT PRIMARY KEY,
    call_id               TEXT UNIQUE NOT NULL,
    case_number           TEXT,
    from_number           TEXT,
    assigned_to           TEXT,
    court_status          TEXT,
    next_hearing_date     TEXT,
    court_status_updated  TEXT,
    case_category         TEXT,
    caller_name           TEXT,
    callback_phone        TEXT,
    is_phone_valid        INTEGER,
    email                 TEXT,
    is_email_valid        INTEGER,
    incident_date         TEXT,
    location              TEXT,
    opposing_party        TEXT,
    key_date_or_deadline  TEXT,
    represented_already   INTEGER,
    injured               INTEGER,
    emergency_flagged     INTEGER,
    police_report_filed   INTEGER,
    case_summary          TEXT,
    additional_details    TEXT,
    call_summary          TEXT,
    call_successful       TEXT,
    user_sentiment        TEXT,
    transcript            TEXT,
    recording_url         TEXT,
    status                TEXT NOT NULL DEFAULT 'new',
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_{table}_from_number ON {table} (from_number);
CREATE INDEX IF NOT EXISTS idx_{table}_created_at ON {table} (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_{table}_category ON {table} (case_category);
"""

# Indexes on columns added after the original schema shipped. These must run
# *after* the ALTER TABLE migration below, not as part of _TABLE_TEMPLATE:
# on an existing deployment the table already exists, so CREATE TABLE IF NOT
# EXISTS is a no-op and the column isn't there yet — indexing it in the same
# script fails with "no such column" and the app won't start.
_LATE_INDEX_TEMPLATE = """
CREATE INDEX IF NOT EXISTS idx_{table}_case_number ON {table} (case_number);
"""

# Staff the agent can transfer a caller to, or take a message for.
_STAFF_SCHEMA = """
CREATE TABLE IF NOT EXISTS staff (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT,
    phone       TEXT,
    extension   TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Messages taken when a transfer target doesn't pick up — the failure path of
# every transfer branch, so this gets used constantly in practice.
_MESSAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id             TEXT PRIMARY KEY,
    call_id        TEXT,
    case_number    TEXT,
    caller_name    TEXT,
    callback_phone TEXT,
    for_staff_id   TEXT,
    message_text   TEXT NOT NULL,
    delivered      INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_delivered ON messages (delivered);
"""

# Every attempt against the mid-call case-lookup endpoint, successful or
# not. The endpoint reads case details to whoever is on the phone, so staff
# need a trail of what was disclosed to whom — and a burst of not_found rows
# from one IP is what brute-force probing looks like.
_LOOKUP_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS lookup_audit (
    id                 TEXT PRIMARY KEY,
    client_ip          TEXT,
    call_id            TEXT,
    case_number_given  TEXT,
    caller_name_given  TEXT,
    outcome            TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lookup_audit_created_at ON lookup_audit (created_at DESC);
"""

SCHEMA = (
    "\n".join(_TABLE_TEMPLATE.format(table=t) for t in BUCKETS)
    + _STAFF_SCHEMA
    + _MESSAGES_SCHEMA
    + _LOOKUP_AUDIT_SCHEMA
)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = get_conn()
_conn.executescript(SCHEMA)
_conn.commit()

# CREATE TABLE IF NOT EXISTS above only creates brand-new tables — existing
# deployments already have these tables without newer columns, so add any
# that are missing by hand.
_NEW_COLUMNS = [
    ("is_phone_valid", "INTEGER"),
    ("is_email_valid", "INTEGER"),
    ("case_number", "TEXT"),
    ("assigned_to", "TEXT"),
    ("court_status", "TEXT"),
    ("next_hearing_date", "TEXT"),
    ("court_status_updated", "TEXT"),
]
for _table in BUCKETS:
    _existing = {row["name"] for row in _conn.execute(f"PRAGMA table_info({_table})")}
    for _col, _type in _NEW_COLUMNS:
        if _col not in _existing:
            _conn.execute(f"ALTER TABLE {_table} ADD COLUMN {_col} {_type}")
_conn.commit()

# Safe now that every table is guaranteed to have the newer columns.
_conn.executescript("\n".join(_LATE_INDEX_TEMPLATE.format(table=t) for t in BUCKETS))
_conn.commit()

# Columns the webhook owns and refreshes on every delivery. Deliberately
# excludes case_number (allocated once, and the caller may have written it
# down) and the staff-owned fields assigned_to / court_status /
# next_hearing_date / court_status_updated — a redelivered webhook must not
# wipe an attorney assignment or a hearing date entered by a human.
_UPDATABLE_COLUMNS = [
    "from_number",
    "case_category",
    "caller_name",
    "callback_phone",
    "is_phone_valid",
    "email",
    "is_email_valid",
    "incident_date",
    "location",
    "opposing_party",
    "key_date_or_deadline",
    "represented_already",
    "injured",
    "emergency_flagged",
    "police_report_filed",
    "case_summary",
    "additional_details",
    "call_summary",
    "call_successful",
    "user_sentiment",
    "transcript",
    "recording_url",
]


def _check_bucket(table: str) -> None:
    if table not in BUCKETS:
        raise ValueError(f"unknown bucket table: {table}")


def case_number_exists(case_number: str) -> bool:
    for table in BUCKETS:
        hit = _conn.execute(
            f"SELECT 1 FROM {table} WHERE case_number = :n LIMIT 1", {"n": case_number}
        ).fetchone()
        if hit:
            return True
    return False


def generate_case_number() -> str:
    """A short, unique number the caller can write down and read back later.

    Six digits, no letters — letters get misheard over a phone line (B/D/P/V,
    M/N). Random rather than sequential so the number doesn't reveal how many
    cases the office has taken, and so it can't be guessed by counting up
    from someone else's.
    """
    for _ in range(100):
        candidate = str(secrets.randbelow(900_000) + 100_000)
        if not case_number_exists(candidate):
            return candidate
    raise RuntimeError("could not allocate a unique case number")


def upsert_record(table: str, row: dict) -> None:
    _check_bucket(table)
    row = dict(row)

    # Allocate a case number only the first time we see this call. A
    # redelivered webhook must keep the number the caller was already given.
    existing = get_record(table, row["call_id"])
    if existing and existing.get("case_number"):
        row["case_number"] = existing["case_number"]
    elif not row.get("case_number"):
        row["case_number"] = generate_case_number()

    columns = ["id", "call_id", "case_number"] + _UPDATABLE_COLUMNS
    placeholders = ", ".join(f":{c}" for c in columns)
    col_list = ", ".join(columns)
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in _UPDATABLE_COLUMNS)

    sql = f"""
        INSERT INTO {table} ({col_list}) VALUES ({placeholders})
        ON CONFLICT(call_id) DO UPDATE SET {update_clause}, updated_at = datetime('now')
    """
    _conn.execute(sql, row)
    _conn.commit()


def list_records(table: str, limit: int = 50, category: str | None = None, status: str | None = None) -> list[dict]:
    _check_bucket(table)
    query = f"SELECT * FROM {table} WHERE 1=1"
    params: dict = {}
    if category:
        query += " AND case_category = :category"
        params["category"] = category
    if status:
        query += " AND status = :status"
        params["status"] = status
    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = _conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_record(table: str, call_id: str) -> dict | None:
    _check_bucket(table)
    row = _conn.execute(f"SELECT * FROM {table} WHERE call_id = :call_id", {"call_id": call_id}).fetchone()
    return dict(row) if row else None


def update_record_status(table: str, call_id: str, status: str) -> None:
    _check_bucket(table)
    _conn.execute(
        f"UPDATE {table} SET status = :status, updated_at = datetime('now') WHERE call_id = :call_id",
        {"status": status, "call_id": call_id},
    )
    _conn.commit()


def count_records(table: str) -> int:
    _check_bucket(table)
    return _conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]


def count_undelivered_messages() -> int:
    return _conn.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE delivered = 0"
    ).fetchone()["n"]


def find_by_case_number(case_number: str) -> dict | None:
    """Locate a case by the number given to the caller, across all buckets."""
    for table in BUCKETS:
        row = _conn.execute(
            f"SELECT *, '{table}' AS bucket FROM {table} WHERE case_number = :n",
            {"n": case_number},
        ).fetchone()
        if row:
            return dict(row)
    return None


def set_case_assignment(table: str, call_id: str, assigned_to: str | None) -> None:
    _check_bucket(table)
    _conn.execute(
        f"UPDATE {table} SET assigned_to = :a, updated_at = datetime('now') WHERE call_id = :c",
        {"a": assigned_to, "c": call_id},
    )
    _conn.commit()


def set_court_status(
    table: str,
    call_id: str,
    court_status: str | None,
    next_hearing_date: str | None,
) -> None:
    """Record where a case stands in court.

    Stamps court_status_updated so the agent can tell a caller how current
    the information is — reading back a hearing date without saying when it
    was last confirmed is how someone ends up at court on the wrong day.
    """
    _check_bucket(table)
    _conn.execute(
        f"""UPDATE {table}
            SET court_status = :s, next_hearing_date = :d,
                court_status_updated = datetime('now'), updated_at = datetime('now')
            WHERE call_id = :c""",
        {"s": court_status, "d": next_hearing_date, "c": call_id},
    )
    _conn.commit()


# ---------------------------------------------------------------- staff ----

def list_staff(active_only: bool = False) -> list[dict]:
    q = "SELECT * FROM staff"
    if active_only:
        q += " WHERE active = 1"
    q += " ORDER BY name"
    return [dict(r) for r in _conn.execute(q).fetchall()]


def get_staff(staff_id: str) -> dict | None:
    row = _conn.execute("SELECT * FROM staff WHERE id = :i", {"i": staff_id}).fetchone()
    return dict(row) if row else None


def create_staff(name: str, role: str | None, phone: str | None, extension: str | None) -> dict:
    staff_id = str(uuid.uuid4())
    _conn.execute(
        """INSERT INTO staff (id, name, role, phone, extension)
           VALUES (:i, :n, :r, :p, :e)""",
        {"i": staff_id, "n": name, "r": role, "p": phone, "e": extension},
    )
    _conn.commit()
    return get_staff(staff_id)


def update_staff(staff_id: str, fields: dict) -> dict | None:
    """Update the provided fields. Explicit nulls clear role/phone/extension
    (someone can lose an extension); name and active can't be nulled, so an
    explicit null there is ignored rather than half-applied."""
    allowed = {"name", "role", "phone", "extension", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    for required in ("name", "active"):
        if required in updates and updates[required] is None:
            del updates[required]
    if not updates:
        return get_staff(staff_id)
    clause = ", ".join(f"{k} = :{k}" for k in updates)
    _conn.execute(
        f"UPDATE staff SET {clause}, updated_at = datetime('now') WHERE id = :i",
        {**updates, "i": staff_id},
    )
    _conn.commit()
    return get_staff(staff_id)


def delete_staff(staff_id: str) -> None:
    _conn.execute("DELETE FROM staff WHERE id = :i", {"i": staff_id})
    _conn.commit()


# ------------------------------------------------------------- messages ----

def list_messages(delivered: bool | None = None, limit: int = 100) -> list[dict]:
    q = """SELECT m.*, s.name AS for_staff_name
           FROM messages m LEFT JOIN staff s ON s.id = m.for_staff_id"""
    params: dict = {"limit": limit}
    if delivered is not None:
        q += " WHERE m.delivered = :d"
        params["d"] = int(delivered)
    q += " ORDER BY m.created_at DESC LIMIT :limit"
    return [dict(r) for r in _conn.execute(q, params).fetchall()]


def create_message(
    message_text: str,
    call_id: str | None = None,
    case_number: str | None = None,
    caller_name: str | None = None,
    callback_phone: str | None = None,
    for_staff_id: str | None = None,
) -> dict:
    msg_id = str(uuid.uuid4())
    _conn.execute(
        """INSERT INTO messages
           (id, call_id, case_number, caller_name, callback_phone, for_staff_id, message_text)
           VALUES (:i, :cid, :cn, :nm, :ph, :sid, :txt)""",
        {"i": msg_id, "cid": call_id, "cn": case_number, "nm": caller_name,
         "ph": callback_phone, "sid": for_staff_id, "txt": message_text},
    )
    _conn.commit()
    row = _conn.execute("SELECT * FROM messages WHERE id = :i", {"i": msg_id}).fetchone()
    return dict(row)


def mark_message_delivered(message_id: str, delivered: bool = True) -> dict | None:
    _conn.execute(
        "UPDATE messages SET delivered = :d, updated_at = datetime('now') WHERE id = :i",
        {"d": int(delivered), "i": message_id},
    )
    _conn.commit()
    row = _conn.execute("SELECT * FROM messages WHERE id = :i", {"i": message_id}).fetchone()
    return dict(row) if row else None


# --------------------------------------------------------- lookup audit ----

def record_lookup(
    client_ip: str | None,
    call_id: str | None,
    case_number_given: str | None,
    caller_name_given: str | None,
    outcome: str,
) -> None:
    _conn.execute(
        """INSERT INTO lookup_audit
           (id, client_ip, call_id, case_number_given, caller_name_given, outcome)
           VALUES (:i, :ip, :cid, :num, :name, :out)""",
        {"i": str(uuid.uuid4()), "ip": client_ip, "cid": call_id,
         "num": case_number_given, "name": caller_name_given, "out": outcome},
    )
    _conn.commit()


def list_lookup_audit(limit: int = 100) -> list[dict]:
    rows = _conn.execute(
        "SELECT * FROM lookup_audit ORDER BY created_at DESC LIMIT :limit",
        {"limit": limit},
    ).fetchall()
    return [dict(r) for r in rows]


# Thin wrappers kept for the original "cases" bucket, used by the webhook
# handler and the inbound caller-history lookup.
def upsert_case(row: dict) -> None:
    upsert_record("cases", row)


def list_cases(limit: int = 50, category: str | None = None, status: str | None = None) -> list[dict]:
    return list_records("cases", limit=limit, category=category, status=status)


def get_case(call_id: str) -> dict | None:
    return get_record("cases", call_id)


def update_status(call_id: str, status: str) -> None:
    update_record_status("cases", call_id, status)


def find_caller_history(from_number: str, limit: int = 5) -> list[dict]:
    """Past calls from this number, most recent first.

    Searches every bucket, not just completed cases — someone whose first
    call dropped early sits in partial_calls, and someone who hit the safety
    branch sits in emergency_flags. Looking only at `cases` would greet both
    as first-time callers.
    """
    union = " UNION ALL ".join(
        f"SELECT id, case_category, case_summary, created_at, '{t}' AS bucket "
        f"FROM {t} WHERE from_number = :from_number"
        for t in BUCKETS
    )
    rows = _conn.execute(
        f"SELECT * FROM ({union}) ORDER BY created_at DESC LIMIT :limit",
        {"from_number": from_number, "limit": limit},
    ).fetchall()
    return [dict(r) for r in rows]


def _backfill_case_numbers() -> int:
    """Give records that predate case numbers one, so every case has an ID
    staff can read out when the caller phones back.

    Runs at import, after the column migration. Only fills NULLs, so it's
    idempotent and never reissues a number a caller was already given.
    """
    filled = 0
    for table in BUCKETS:
        pending = _conn.execute(
            f"SELECT call_id FROM {table} WHERE case_number IS NULL OR case_number = ''"
        ).fetchall()
        for row in pending:
            _conn.execute(
                f"UPDATE {table} SET case_number = :n WHERE call_id = :c",
                {"n": generate_case_number(), "c": row["call_id"]},
            )
            filled += 1
    if filled:
        _conn.commit()
    return filled


_backfill_case_numbers()
