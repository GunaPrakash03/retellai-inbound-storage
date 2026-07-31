import os
import sqlite3
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
    from_number           TEXT,
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

SCHEMA = "\n".join(_TABLE_TEMPLATE.format(table=t) for t in BUCKETS)


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
]
for _table in BUCKETS:
    _existing = {row["name"] for row in _conn.execute(f"PRAGMA table_info({_table})")}
    for _col, _type in _NEW_COLUMNS:
        if _col not in _existing:
            _conn.execute(f"ALTER TABLE {_table} ADD COLUMN {_col} {_type}")
_conn.commit()

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


def upsert_record(table: str, row: dict) -> None:
    _check_bucket(table)
    columns = ["id", "call_id"] + _UPDATABLE_COLUMNS
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
