import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "./data/cases.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id                    TEXT PRIMARY KEY,
    call_id               TEXT UNIQUE NOT NULL,
    from_number           TEXT,
    case_category         TEXT,
    caller_name           TEXT,
    callback_phone        TEXT,
    email                 TEXT,
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
CREATE INDEX IF NOT EXISTS idx_cases_from_number ON cases (from_number);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_category ON cases (case_category);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = get_conn()
_conn.executescript(SCHEMA)
_conn.commit()

_UPDATABLE_COLUMNS = [
    "from_number",
    "case_category",
    "caller_name",
    "callback_phone",
    "email",
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


def upsert_case(row: dict) -> None:
    columns = ["id", "call_id"] + _UPDATABLE_COLUMNS
    placeholders = ", ".join(f":{c}" for c in columns)
    col_list = ", ".join(columns)
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in _UPDATABLE_COLUMNS)

    sql = f"""
        INSERT INTO cases ({col_list}) VALUES ({placeholders})
        ON CONFLICT(call_id) DO UPDATE SET {update_clause}, updated_at = datetime('now')
    """
    _conn.execute(sql, row)
    _conn.commit()


def list_cases(limit: int = 50, category: str | None = None, status: str | None = None) -> list[dict]:
    query = "SELECT * FROM cases WHERE 1=1"
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


def get_case(call_id: str) -> dict | None:
    row = _conn.execute("SELECT * FROM cases WHERE call_id = :call_id", {"call_id": call_id}).fetchone()
    return dict(row) if row else None


def update_status(call_id: str, status: str) -> None:
    _conn.execute(
        "UPDATE cases SET status = :status, updated_at = datetime('now') WHERE call_id = :call_id",
        {"status": status, "call_id": call_id},
    )
    _conn.commit()


def find_caller_history(from_number: str, limit: int = 5) -> list[dict]:
    rows = _conn.execute(
        """SELECT id, case_category, case_summary, created_at
           FROM cases WHERE from_number = :from_number
           ORDER BY created_at DESC LIMIT :limit""",
        {"from_number": from_number, "limit": limit},
    ).fetchall()
    return [dict(r) for r in rows]
