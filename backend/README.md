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
| `POST` | `/webhooks/retell` | Fires on `call_started` / `call_ended` / `call_analyzed`. Only `call_analyzed` writes to the DB, into one of the six buckets below. |
| `GET` | `/cases` | List completed cases. Query params: `category`, `status`, `limit`. |
| `GET` | `/intake-fields` | The intake field spec — what the agent asks, per practice area, and which of those are must-ask. |
| `GET` | `/taxonomy` | The ten practice areas and their matter types. |
| `GET` | `/cases/{call_id}` | Full detail for one case, including transcript. |
| `PATCH` | `/cases/{call_id}` | Update triage status. Body: `{"status": "reviewed"}`. |
| `GET` | `/partial-calls`, `/unwanted-calls`, `/spam-calls`, `/out-of-scope-calls`, `/emergency-flags` | Same shape as `/cases`, for the other five buckets. |
| `GET` \| `PATCH` | `/{bucket}/{call_id}` | Detail / status update for a non-`cases` bucket (`partial-calls`, `unwanted-calls`, `spam-calls`, `out-of-scope-calls`, or `emergency-flags`). |

## Call buckets

Every analyzed call lands in exactly one table. Routing is decided by
`app/webhooks.py`, primarily by searching the call transcript for the
agent's own scripted closing lines (see `detect_outcome_from_transcript` in
`app/validators.py`) — this is deterministic since we control the exact
wording of every ending, unlike Retell's own `call_outcome` extraction
field, which repeatedly mislabeled calls in testing and is now only a
fallback for when the transcript is missing:

| Bucket (table) | When a call lands here |
|---|---|
| `cases` | Intake completed — has caller name, callback phone, category, and summary. |
| `partial_calls` | Call disconnected or was cut short before intake finished. |
| `unwanted_calls` | Nonsensical, contradictory, or clearly not a real intake (prank/test calls). |
| `spam_calls` | Caller was coherent but repeatedly refused/deflected the actual intake questions. |
| `out_of_scope_calls` | Genuine, polite callers who reached the wrong place — a technical or sales question, a wrong number, or a real legal matter in an area this firm doesn't practice (a divorce, a DUI, a car accident). Not an intake, so kept out of the attorney queue; a spike here is visible, and can mean the number is listed somewhere wrong. |
| `emergency_flags` | The safety branch ended the call, or fired on a call that never finished — staff need visibility on safety events. A whistleblower who was in danger, confirmed safe, and then completed the whole intake lands in `cases` with `emergency_flagged` set instead, so a finished case isn't hidden from the attorney queue. |

## Data validation

`callback_phone` and `email` are each checked by `app/validators.py` and get
a companion `is_phone_valid` / `is_email_valid` column (`1`, `0`, or `null`
if the field was never captured at all). A call is never blocked or
rerouted for failing validation — it's saved normally and the invalid field
is just flagged, since staff still need the record even if the phone number
needs a follow-up to confirm. `is_phone_valid` requires exactly 10 digits
after allowing for an optional 1-3 digit country code prefix, matching the
phone-number rules in the agent prompt; `is_email_valid` requires a
`local@domain.tld`-shaped address.

## The intake field spec

`app/intake_fields.py` is the single source of truth for what the agent
collects. The database columns, the row the webhook writes, the fields staff
can correct in the dashboard, the `/intake-fields` endpoint, and the Retell
extraction config below are all generated from it, so adding a question to
the agent prompt is one edit here rather than five edits that drift apart.

It mirrors `agent-prompt-latest.txt` directly:

- **Core fields** — the prompt's Step 2, asked on every call, plus the Step 5
  retention answer and the flags the prompt sets internally.
- **Category fields** — the prompt's Step 3, one list per practice area, each
  field marked `must_ask` or not to match the prompt's own "Must ask" vs "Ask
  if the conversation allows" split.

`GET /cases/{call_id}` returns two derived keys alongside the record:
`intake` (the labelled fields for that record's practice area) and
`missing_must_ask` (must-ask questions that were never captured — the
prompt's Step 4 check, applied to the record that actually landed). An
"unknown" counts as asked; only a NULL counts as missing.

Booleans are three-state — `1`, `0`, or `null` for never captured. The prompt
is explicit that a question answered "I don't know" is a different fact from
one never asked, and both differ from a "no", so a missing boolean is stored
as `null` rather than collapsing to `0`.

`time_sensitive` is the extraction's own answer ORed with the four deadline
situations the prompt names — a securities lead plaintiff deadline, a merger
vote or tender date, a retaliation adverse action, or a whistleblower matter
not yet reported anywhere. Missing that flag costs a deadline nobody saw, so
it isn't left to the extraction alone. See `validators.derive_time_sensitive`.

## The ten practice areas

`case_category` is one of: `securities_fraud`, `shareholder_derivative`,
`merger_transaction`, `whistleblower_sec`, `whistleblower_qui_tam`,
`whistleblower_retaliation`, `consumer_class`, `data_privacy_class`,
`employment_class`, `other`.

Each has a second level, the matter type (`case_subcategory`) — see
`app/taxonomy.py` and `GET /taxonomy`. Retell can extract it, and when it
doesn't, the Gemini classifier in `app/classify.py` fills it from the
transcript after the call.

## Post-Call Data Extraction fields to configure in Retell

Add these under **Agent → Post-Call Data Extraction**, matching name and
type exactly — the webhook handler in `app/webhooks.py` reads these keys
from `call.call_analysis.custom_analysis_data`. Regenerate this table with:

```bash
python3 -m tools.extraction_config            # this table
python3 -m tools.extraction_config --plain    # one field per block, to copy
```

Plus two Selector fields that aren't in the spec because they don't hold an
answer the caller gave:

| Field | Type | Description to paste in Retell |
|---|---|---|
| `case_category` | Selector | One of: securities_fraud, shareholder_derivative, merger_transaction, whistleblower_sec, whistleblower_qui_tam, whistleblower_retaliation, consumer_class, data_privacy_class, employment_class, other |
| `case_subcategory` | Selector | The matter type within that area — see `GET /taxonomy` for the list per category. Leave unset if unclear; the backend fills it from the transcript. |

The "Asked in" column is which practice areas ask the question; every field
is safe to configure once, since a field a category never asks simply stays
empty on those records.

| Field | Type | Asked in | Description to paste in Retell |
|---|---|---|---|
| `caller_name` | Text | all | Full name of the caller, as spelled out on the call |
| `callback_phone` | Text | all | Best callback number, digits only, with country code if given |
| `email` | Text | all | Caller's email address |
| `mailing_address` | Text | all | Best mailing address — city, state and ZIP at minimum |
| `case_summary` | Text | all | One or two sentence summary of the situation, in the caller's words |
| `represented_already` | Boolean | all | True if the caller already has another attorney on this matter, or has already spoken with another firm about it |
| `other_firm_name` | Text | all | Name of the other attorney or firm, if the caller is already represented or has spoken with one |
| `prior_contact` | Text | all | Who has already contacted the caller or taken a statement about this — the company, its lawyers, an investigator, a government agency. "no" if none |
| `referral_source` | Text | all | How the caller heard about the firm |
| `caller_affiliation` | Text | all | Whether the caller is currently an employee, officer, or director of the company involved (conflict check). "none" if they are not |
| `retention_consent` | Text | all | Whether the caller wants a retention agreement emailed if the attorney takes it on: yes, no, or undecided |
| `time_sensitive` | Boolean | all | True if a lead plaintiff deadline, court notice, vote or tender date, filing deadline, or first-to-file whistleblower exposure came up |
| `whistleblower_limited_disclosure` | Boolean | all | True if a whistleblower caller chose not to give details and only name, number, email, and employer or industry were taken |
| `emergency_flagged` | Boolean | all | True only if the safety branch actually fired — the caller was told to hang up and call 911, or a whistleblower said they were in danger |
| `additional_details` | Text | all | Anything relevant that no other field covers |
| `issuer_name` | Text | securities_fraud, shareholder_derivative, merger_transaction | Name of the company whose securities are involved |
| `ticker_symbol` | Text | securities_fraud, shareholder_derivative, merger_transaction | Ticker symbol, letters only, as read back on the call |
| `position_status` | Text | securities_fraud, merger_transaction | Whether the caller bought, sold, or still holds the securities |
| `purchase_period` | Text | securities_fraud, consumer_class | Roughly when the caller bought, and whether once or over a period |
| `position_size` | Text | securities_fraud, merger_transaction | Roughly how many shares or units, or the total dollar amount invested |
| `still_holding` | Boolean | securities_fraud | True if the caller still holds any of the securities today |
| `triggering_event` | Text | securities_fraud | What made the caller think something was wrong — a stock drop, a news story, an SEC filing, a law firm press release |
| `lead_plaintiff_deadline` | Text | securities_fraud | The exact date on any notice or press release the caller mentioned |
| `records_available` | Boolean | securities_fraud, consumer_class, data_privacy_class, employment_class | True if the caller has supporting records — statements, receipts, pay stubs, the notice letter |
| `brokerage_name` | Text | securities_fraud | Which brokerage or platform the caller used |
| `account_type` | Text | securities_fraud | Whether the shares were held in a retirement or trust account |
| `prior_lead_plaintiff` | Boolean | securities_fraud | True if the caller has served as a lead plaintiff or class representative before |
| `ownership_start` | Text | shareholder_derivative | Roughly when the caller acquired their shares |
| `continuous_ownership` | Boolean | shareholder_derivative | True if the caller has held the shares continuously since then |
| `conduct_alleged` | Text | shareholder_derivative, merger_transaction, whistleblower_sec, whistleblower_qui_tam, whistleblower_retaliation, consumer_class, employment_class, other | What the caller says was done wrong, in their own words |
| `information_source` | Text | shareholder_derivative | How the caller learned about the conduct |
| `demand_status` | Text | shareholder_derivative | Whether a books-and-records or litigation demand has been sent, and any response |
| `related_proceedings` | Text | shareholder_derivative | Any pending investigation, SEC action, or related lawsuit the caller knows of |
| `opposing_party` | Text | merger_transaction, whistleblower_sec, whistleblower_qui_tam, whistleblower_retaliation, consumer_class, data_privacy_class, employment_class, other | The company, employer, agency, or acquirer the matter is against |
| `key_date_or_deadline` | Text | merger_transaction, whistleblower_sec, whistleblower_qui_tam | Any vote, tender, closing, filing, or hearing date the caller mentioned |
| `vote_status` | Text | merger_transaction | Whether the caller has already voted or tendered |
| `incident_period` | Text | whistleblower_sec, whistleblower_qui_tam | Roughly when the conduct happened, or whether it is still happening |
| `prior_report` | Text | whistleblower_sec, whistleblower_qui_tam | Anyone the caller has already reported this to — SEC, CFTC, DOJ, an inspector general, an internal hotline, another law firm. "no" if none |
| `still_employed` | Boolean | whistleblower_sec, whistleblower_qui_tam, whistleblower_retaliation, employment_class | True if the caller still works for the employer involved |
| `job_title` | Text | whistleblower_sec, whistleblower_qui_tam, whistleblower_retaliation, employment_class | The caller's role or job title |
| `documentation_exists` | Boolean | whistleblower_sec, whistleblower_qui_tam, whistleblower_retaliation | True if the caller says they have documents or records. Never ask what they contain or where they are kept |
| `others_aware` | Boolean | whistleblower_sec, whistleblower_qui_tam | True if anyone else knows the caller is raising this |
| `reported_to` | Text | whistleblower_retaliation | Who the caller reported the underlying conduct to |
| `reported_date` | Text | whistleblower_retaliation | Roughly when the caller reported it |
| `adverse_action` | Text | whistleblower_retaliation | What happened to the caller afterward — fired, demoted, suspended, hours cut, transferred |
| `incident_date` | Text | whistleblower_retaliation, other | Date of the adverse action or key event, YYYY-MM-DD if determinable |
| `employment_length` | Text | whistleblower_retaliation | How long the caller worked there |
| `witnesses` | Text | whistleblower_retaliation | Anyone who saw or knows about what happened |
| `agency_filing` | Text | whistleblower_retaliation | Whether the caller filed with OSHA, the EEOC, or a state agency, and when |
| `product_name` | Text | consumer_class | The product or service involved |
| `purchase_channel` | Text | consumer_class | Where it was bought — a store, a website, an app, a subscription |
| `amount_paid` | Text | consumer_class | Roughly how much the caller paid or was charged |
| `purchase_state` | Text | consumer_class | The state the caller bought it in or was living in at the time |
| `company_contacted` | Text | consumer_class | Whether the caller contacted the company about it, and what happened |
| `others_affected` | Boolean | consumer_class, employment_class, other | True if the caller believes other people were treated the same way |
| `physical_injury` | Boolean | consumer_class | True if the caller was physically harmed by the product. Flag for attorney review; do not pursue injury details |
| `notice_received` | Boolean | data_privacy_class | True if the caller received a breach notice letter or email |
| `notice_date` | Text | data_privacy_class | The date on the breach notice |
| `data_types_involved` | Text | data_privacy_class | Kinds of information involved — name, Social Security number, financial account, medical, biometric. Never record an actual account or SSN |
| `harm_experienced` | Text | data_privacy_class | Any actual misuse seen — fraudulent charges, accounts opened, tax filings, identity theft |
| `residence_state` | Text | data_privacy_class | What state the caller lives in |
| `relationship_type` | Text | data_privacy_class | Whether the caller was a customer, patient, employee, or user, and roughly when |
| `out_of_pocket_costs` | Text | data_privacy_class | Whether the caller paid for credit monitoring or spent time dealing with it |
| `pay_type` | Text | employment_class | Whether the caller was paid hourly or salaried |
| `employment_period` | Text | employment_class | Roughly what dates the caller worked there |
| `work_state` | Text | employment_class | Which state the caller worked in |
| `hours_worked` | Text | employment_class | Roughly how many hours a week the caller worked |
| `arbitration_agreement` | Boolean | employment_class | True if the caller signed an arbitration agreement or class waiver |
| `reported_internally` | Boolean | employment_class | True if the caller raised it with HR or a supervisor |

Keep the default `Call Summary`, `Call Successful`, and `User Sentiment`
fields too — the backend stores those alongside the custom ones.

`call_outcome` is optional. Bucket routing is decided by matching the agent's
scripted closing lines in the transcript (see "Call buckets" above);
`call_outcome` is only consulted as a fallback for "unwanted"/"spam" when the
transcript is missing.

## Custom functions to register in Retell

Agent editor → **Functions / Tools → Add → Custom Function**. All three
endpoints accept either payload mode (`{name, call, args}` or bare args), so
the mode setting doesn't matter.

| Name | Endpoint | What it's for |
|---|---|---|
| `check_phone_number` | `POST /validate-phone` | Counts and validates the callback number. |
| `take_message` | `POST /messages` | Records a message when a transfer doesn't connect. |
| `lookup_case_status` | `POST /case-lookup` | Court status for an existing case. |

Each function's arguments go in the editor's **Parameters** box as a JSON
schema — *not* the **Query Parameters** box just above it, which sends fixed
values the model never fills in. Set the timeout to about 5000 ms; these are
local lookups that answer in milliseconds, and the default two minutes is two
minutes of silence on a live call if anything goes wrong.

`check_phone_number`:

```json
{
  "type": "object",
  "properties": {
    "phone": {
      "type": "string",
      "description": "The number as the caller said it, in digits or words. Never count or edit it."
    }
  },
  "required": ["phone"]
}
```

Keep each description on one line and free of quotes. A description long
enough to wrap when pasted becomes a literal newline inside a JSON string,
which the editor rejects as a bad control character.

Description: *Check a callback phone number and count its digits. Call this
every time a caller gives a phone number, before reading it back. Never count
the digits yourself.*

`take_message`:

```json
{
  "type": "object",
  "properties": {
    "message_text": {"type": "string", "description": "What to pass on, and who it is for"},
    "caller_name": {"type": "string", "description": "The caller name as spelled out"},
    "callback_phone": {"type": "string", "description": "The confirmed callback number"}
  },
  "required": ["message_text"]
}
```

**`check_phone_number` is not optional.** Counting digits is the one thing a
voice agent reliably gets wrong: on a live call it counted a correct
ten-digit number as nine, told the caller so, made them repeat it three
times, then counted the same digits again and got ten. Six turns, and the
caller was told their own number was wrong. The prompt now forbids counting
and tells the agent to send what it heard here and read back the `say` line
that comes back. It accepts spoken digits ("nine one two three…") as well as
figures, and answers:

```json
{"ok": true, "digit_count": 10, "national_number": "9123456789",
 "country_code": "1", "e164": "+19123456789", "readback": "9-1-2-3-4-5-6-7-8-9",
 "say": "That's 10 digits. Read it back as 9-1-2-3-4-5-6-7-8-9 and ask them to confirm."}
```

A short number comes back `ok: false` with a `say` line naming how many
digits are missing. Country codes are handled by stripping a 1-3 digit
prefix when that leaves exactly 10 national digits.

`take_message` requires `message_text`. Called with no arguments it returns a
422 whose `detail` tells the agent what to collect, rather than a schema
error — a live call ended with the caller promised a callback that was never
recorded, because the 422 came back as an opaque failure and the agent said
"I've got that down" anyway.

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
