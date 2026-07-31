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
| `POST` | `/webhooks/retell` | Fires on `call_started` / `call_ended` / `call_analyzed`. Only `call_analyzed` writes to the DB, into one of the five buckets below. |
| `GET` | `/cases` | List completed cases. Query params: `category`, `status`, `limit`. |
| `GET` | `/cases/{call_id}` | Full detail for one case, including transcript. |
| `PATCH` | `/cases/{call_id}` | Update triage status. Body: `{"status": "reviewed"}`. |
| `GET` | `/partial-calls`, `/unwanted-calls`, `/spam-calls`, `/emergency-flags` | Same shape as `/cases`, for the other four buckets. |
| `GET` \| `PATCH` | `/{bucket}/{call_id}` | Detail / status update for a non-`cases` bucket (`partial-calls`, `unwanted-calls`, `spam-calls`, or `emergency-flags`). |

## Call buckets

Every analyzed call lands in exactly one table, based on `emergency_flagged`
and `call_outcome` (see below):

| Bucket (table) | When a call lands here |
|---|---|
| `cases` | Intake completed — has caller name, callback phone, category, and summary. |
| `partial_calls` | Call disconnected or was cut short before intake finished. |
| `unwanted_calls` | Nonsensical, contradictory, or clearly not a real intake (prank/test calls). |
| `spam_calls` | Caller was coherent but repeatedly refused/deflected the actual intake questions. |
| `emergency_flags` | The 911/safety branch fired — saved here regardless of completeness, since staff need visibility on safety events. |

## Data validation

`callback_phone` and `email` are each checked by `app/validators.py` and get
a companion `is_phone_valid` / `is_email_valid` column (`1`, `0`, or `null`
if the field was never captured at all). A call is never blocked or
rerouted for failing validation — it's saved normally and the invalid field
is just flagged, since staff still need the record even if the phone number
needs a follow-up to confirm. `is_phone_valid` requires exactly 10 digits
(a leading US country code `1` is stripped first if present); `is_email_valid`
requires a `local@domain.tld`-shaped address.

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
| `call_outcome` | Selector | Look at the agent's LAST line before the call ended and match it to exactly one of these — do not judge the caller's behavior yourself, only match the agent's closing sentence: "completed" if the last line was the full readback ("So to confirm — your name is...") followed by "Thank you — I have everything I need...". "partial" if the last line was "It looks like we may have gotten disconnected, or you're not able to hear me right now...". "unwanted" if the last line was "I want to make sure I'm getting accurate information for the attorney, and I'm having a hard time following the details...". "spam" if the last line was "It sounds like now might not be the right time to go through these details...". If the last line was "Please hang up and call 911 right now" or the domestic-violence safety line, that call has no separate call_outcome relevance since emergency_flagged already covers it — pick "partial" as a default in that case. |

Keep the default `Call Summary`, `Call Successful`, and `User Sentiment`
fields too — the backend stores those alongside the custom ones.

`call_outcome` drives which bucket table a call lands in (see "Call buckets"
above), together with `emergency_flagged`. If `call_outcome` isn't
configured yet, the backend falls back to a heuristic: complete core fields
→ `cases`, otherwise → `partial_calls`. Configuring `call_outcome` is what
lets `unwanted_calls` and `spam_calls` get populated at all.

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
