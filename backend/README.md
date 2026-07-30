# Backend — FastAPI + SQLite

## Setup

```bash
pip install --user -r requirements.txt   # add --break-system-packages if pip refuses
cp .env.example .env                      # set RETELL_API_KEY to your real Retell API key
python3 -m uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/webhooks/retell/inbound` | Fires before the call connects. Looks up caller history, returns dynamic variables. |
| `POST` | `/webhooks/retell` | Fires on `call_started` / `call_ended` / `call_analyzed`. Only `call_analyzed` writes to the DB. |
| `GET` | `/cases` | List cases. Query params: `category`, `status`, `limit`. |
| `GET` | `/cases/{call_id}` | Full detail for one case, including transcript. |
| `PATCH` | `/cases/{call_id}` | Update triage status. Body: `{"status": "reviewed"}`. |

## Post-Call Data Extraction fields to configure in Retell

Add these under **Agent → Post-Call Data Extraction**, matching name and
type exactly — the webhook handler in `app/webhooks.py` reads these keys
from `call.call_analysis.custom_analysis_data`.

| Field | Type | Description to paste in Retell |
|---|---|---|
| `case_category` | Selector | One of: personal_injury, workplace_employment, medical_product, family_law, criminal_defense, immigration, real_estate_housing, business_contract, estate_disability, other |
| `caller_name` | Text | Full name of the caller |
| `callback_phone` | Text | Best callback number, digits only |
| `email` | Text | Caller's email address |
| `incident_date` | Text | Date of the incident/arrest/deadline in YYYY-MM-DD if determinable |
| `location` | Text | City/state or address relevant to the matter |
| `opposing_party` | Text | Other driver, employer, landlord, spouse, defendant — whoever the matter is against |
| `key_date_or_deadline` | Text | Any court date, hearing, or filing deadline mentioned |
| `represented_already` | Boolean | Already has another attorney or adjuster contact |
| `injured` | Boolean | Did the caller sustain any injury (personal injury / workplace only) |
| `emergency_flagged` | Boolean | Did the 911/safety branch get triggered during the call |
| `police_report_filed` | Boolean | Was a police report filed |
| `case_summary` | Text | One or two sentence description of the situation |
| `additional_details` | Text | Catch-all for anything category-specific not covered above |

Keep the default `Call Summary`, `Call Successful`, and `User Sentiment`
fields too — the backend stores those alongside the custom ones.

## Signature verification

Every `/webhooks/retell` request must carry a valid `x-retell-signature`
header — an HMAC-SHA256 of the raw request body, keyed on your
`RETELL_API_KEY`. Requests that fail verification get a `401` and are never
written to the database. This is implemented in `app/security.py`.

## Notes

- Every write is keyed off `call_id` with an upsert (`ON CONFLICT ... DO
  UPDATE`) — a retried webhook delivery updates the same row instead of
  creating a duplicate case.
- `data/cases.db` is the SQLite file; it's git-ignored.
- To move to Postgres later, only `app/db.py` needs to change — routes in
  `app/webhooks.py` and `app/main.py` don't touch SQLite directly.
