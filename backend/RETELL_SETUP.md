# Retell AI configuration — full setup reference

This is the complete checklist for configuring the Retell agent for this
project, end to end. Everything here lives in Retell's dashboard, not in
this repo — the repo only defines what the backend expects to receive.

For giving the agent a real inbound phone number via Twilio (SIP trunking),
see `RETELL_TWILIO_SETUP.md` — that's a separate, optional layer on top of
everything here.

## 1. Webhook URLs

Set these under **Agent → Webhook Settings**, using your backend's public
domain (Railway → your backend service → Settings → Networking → Public
Domain):

| Setting | URL |
|---|---|
| Agent Level Webhook URL | `https://<your-domain>/webhooks/retell` |
| Inbound webhook (fires before the call connects) | `https://<your-domain>/webhooks/retell/inbound` |

Webhook Events: leave the default set (`call_started`, `call_ended`,
`call_analyzed`) — only `call_analyzed` writes to the database, but the
others are harmless and useful for the `/debug/last-webhook` capture during
troubleshooting.

## 2. Webhook signing key

Retell signs every webhook with the API key that has the **"webhook"
badge** next to it in **API Keys** — not just any key on the account. Copy
that exact key (including the `key_` prefix) into your backend's
`RETELL_API_KEY` environment variable (Railway → backend service →
Variables). If this is wrong, every webhook gets a `401` and nothing is
ever saved — see "Troubleshooting" below.

## 3. System prompt

Paste the full contents of `backend/agent-prompt-latest.txt` into the
agent's prompt box. This defines:

- The safety check (real-time emergency / DV — routes to `emergency_flags`)
- The 5-step intake flow (opening → safety check → category → core fields →
  category-specific follow-ups → closing readback)
- Phone number rules (ask for country code, confirm exactly 10 digits)
- The three non-safety call-ending scripts (unresponsive, nonsensical,
  evasive) — their exact wording matters, see "How routing actually works"
  below
- The closing readback that must be the last thing said on every normally
  completed call

Whenever this file changes, re-paste the whole thing into Retell — there's
no partial-sync mechanism.

## 4. Post-Call Data Extraction fields

Add these under **Agent → Post-Call Data Extraction**, matching field name
and type exactly. The webhook handler (`app/webhooks.py`) reads these keys
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
| `call_outcome` | Selector | Optional fallback only (see below) — one of: completed, partial, unwanted, spam. |

Keep the default `Call Summary`, `Call Successful`, and `User Sentiment`
fields too — the backend stores those alongside the custom ones.

**Skip nothing above.** Every field the backend can't find comes back
`null` in the dashboard — this was the reason the case table looked empty
early on, before these fields were configured.

## 5. How routing into the 5 buckets actually works

Every analyzed call lands in exactly one of: `cases`, `partial_calls`,
`unwanted_calls`, `spam_calls`, `emergency_flags`.

**This is decided in the backend, not in Retell.** `app/webhooks.py`
searches the call transcript directly for the agent's own scripted closing
phrases (`detect_outcome_from_transcript` in `app/validators.py`):

| If the transcript contains... | Bucket |
|---|---|
| "hang up and call 911 right now" or "your safety comes first" | `emergency_flags` |
| "having a hard time following the details" | `unwanted_calls` |
| "might not be the right time to go through these details" | `spam_calls` |
| none of the above, and `caller_name`/`callback_phone`/`case_category`/`case_summary` are all present | `cases` |
| none of the above, and any core field is missing | `partial_calls` |

**Why not just use Retell's `call_outcome` field?** We tried that first —
it's still configured as a fallback — but Retell's own classification
repeatedly mislabeled calls as `"completed"` even when the transcript
contained a different scripted ending verbatim. Matching our own known
wording in the transcript is deterministic; asking an LLM to classify
caller intent from the whole conversation wasn't reliable enough. **This
means if you ever edit the closing scripts in the prompt, you must also
update the matching phrases in `_OUTCOME_PHRASES` in `app/validators.py`,
or detection silently stops working for that ending.**

## 6. Testing

Use `backend/test-scenarios.md` (or the published test-sheet artifact) —
7 scripted calls covering every bucket, plus the regression check for a
past-but-severe incident that shouldn't trigger the safety branch.

After any test call, check where it landed:

```bash
curl -s https://<your-domain>/cases
curl -s https://<your-domain>/partial-calls
curl -s https://<your-domain>/unwanted-calls
curl -s https://<your-domain>/spam-calls
curl -s https://<your-domain>/emergency-flags
```

For a call that landed in the wrong bucket, the fastest diagnosis is: read
the transcript's last agent line, and check which row of the table in
section 5 it matches. If it doesn't match any of them, that's a genuinely
new ending the prompt produced that isn't in `_OUTCOME_PHRASES` yet.

## 7. Data validation

`callback_phone` and `email` each get a computed `is_phone_valid` /
`is_email_valid` flag (`1`, `0`, or `null` if never captured) — shown as a
⚠ in the frontend. Never blocks or reroutes the call, since staff still
need the record even with a bad phone number to follow up on.

- Phone: valid if the number, after stripping a 1-3 digit country code
  prefix, is exactly 10 digits.
- Email: valid if it matches `local@domain.tld`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Retell "Run Test" webhook returns 401 | `RETELL_API_KEY` in Railway isn't the key with the **webhook badge** in Retell, or has a stray trailing space/newline from copy-paste. |
| A call's structured fields are all `null` | Post-Call Data Extraction fields aren't configured yet, or a field name/type doesn't match section 4 exactly. |
| A category shows "Uncategorized" in the frontend | Retell sometimes appends stray punctuation to Selector values (e.g. `"personal_injury,"`) — this is normalized server-side (`normalize_category`), so it should no longer happen for new calls; only affects rows saved before that fix. |
| A call ends mid-question with no scripted closing line | Check `disconnection_reason` in the raw call payload (`/debug/last-webhook`) — if it's `agent_hangup`, the model is skipping the Closing script; re-confirm the latest prompt (with the "only five ways to end a call" rule) is what's pasted into Retell. |
| A call lands in an unexpected bucket | Read the transcript's actual last agent line and compare to section 5's phrase table — routing follows that, not Retell's own judgment of "what kind of call this was." |
