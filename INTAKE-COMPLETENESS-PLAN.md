# Intake Completeness — Audit and Fix Plan

> **Largely implemented, against a different practice.** The audit below was
> written for the previous general-practice prompt, and its central
> recommendation — a per-category required-fields spec as one source of truth
> — now exists as `backend/app/intake_fields.py`, built for the Bottini &
> Bottini prompt's ten areas. Category-specific answers have real columns
> instead of competing for `additional_details`, must-ask coverage is
> reported per record as `missing_must_ask`, and the extraction config is
> generated from the same spec. The specific field gaps listed below refer to
> practice areas the firm no longer takes.

Goal: every case, in every practice area, arrives with enough accurate detail
that an attorney can act on it without calling the client back for basics.

## 1. What's actually wrong

The agent asks good questions. The backend has nowhere to put most of the
answers.

There are **16 structured intake fields** total, and they are shared across all
9 practice areas. Every category-specific fact the prompt tells Maya to collect
that doesn't map to one of those 16 falls into a single free-text field,
`additional_details` — unsearchable, unfilterable, not correctable by staff as a
field, and preserved only if Retell's post-call extraction happens to phrase its
summary that way.

Audit of `agent-prompt-latest.txt` Step 3 against the schema in `db.py:32-70`:

| Category | Facts the prompt asks for | Have a field | No home |
|---|---|---|---|
| personal_injury / medical_product | 8 | 5 | medical treatment received, police report **number**, insurance carrier, vehicle/plate |
| workplace_employment | 5 | 2 | reported to HR + when, still employed, workers' comp filed |
| family_law | 4 | 3 | children involved |
| criminal_defense | 4 | 2 | charges, currently in custody |
| immigration | 3 | 2 | current immigration status |
| real_estate_housing | 3 | 3 (partly) | notice type (only its date fits) |
| business_contract | 3 | 3 | — |
| estate_disability | 3 | 2 | claim already filed, decedent name |
| other | open-ended | by design | — (intentionally free text) |

**~14 distinct facts have no structured home**, and all of them compete for the
same one text field.

Two of these are worse than the rest:

- `in_custody` (criminal_defense) — a caller sitting in jail is the most
  time-critical intake the firm takes, and right now that fact is a sentence in
  a paragraph. Nothing can sort or alert on it.
- `still_employed` / `reported_internally` (workplace_employment) — these drive
  whether a claim is even viable, and employment is the pilot category for the
  subtype classifier.

### Confirmed live example

Case `call_c6eab66be6ffd792d66646be710` (bicycle accident, Guna Prakash). The
agent asked for the vehicle and the caller gave `TN76 E 99 99`. It survived —
but only as prose inside `additional_details`. Had the extraction summarized
differently, the plate number would have vanished with no error anywhere. The
other driver's insurance carrier was never asked at all: the agent folded it
into the core "are you already represented / spoken to an insurer" question,
which is about the *caller's* insurer, not the *defendant's*.

### Also found

- **No jurisdiction check.** That case's incident was in Tamil Nadu, India, and
  it routed to `cases` as a normal US intake. The prompt's out-of-scope section
  (lines 69-88) only covers "not a legal matter," not "not our jurisdiction."
- **The Gemini classifier is failing on the live deploy.** `/debug/classify`
  returns `raw_answer: null` on every case. Railway is also running code older
  than commit `353b542`, so the `last_error` field that would name the cause
  isn't in the deployed response. Categories currently get their matter type
  from Retell's own extraction instead, which masks the failure.

## 2. Root cause

One schema for nine practice areas. The design assumed category-specific detail
could live in a catch-all string. It can't — not if you want to measure it,
search it, correct it, or alert on it.

## 3. How to check this (ongoing, not one-off)

Three mechanisms, in increasing durability:

**A. Required-fields spec.** Declare, per category, which fields a case must
have to count as complete — a plain dict in a new `app/completeness.py`. This
becomes the single source of truth that the prompt, the extraction config, and
the dashboard all answer to.

**B. Completeness score per case.** Compute `missing_fields` and a percentage at
webhook time, store it, and surface it. Then "are we collecting enough detail?"
becomes a query, not an opinion:

```
GET /cases?incomplete=1          # cases missing required fields
GET /completeness-report         # per-category averages, worst fields
```

Show it in `CaseDetail.jsx` as a "Missing: insurance carrier, medical treatment"
banner so staff see the gap before they pick up the phone.

**C. Transcript replay tests.** `backend/test-scenarios.md` already has scenario
text. Turn those into fixtures and assert that a given transcript produces a
given set of populated fields. This catches prompt regressions and extraction
drift before a real caller hits them.

## 4. Where extraction should happen — the design decision

Every new field needs something to populate it. Two options:

**Option A — add Retell Post-Call Data Extraction fields.** Configure ~14 more
fields in the Retell dashboard (`RETELL_SETUP.md` section 4). Simple, no new
code. But extraction fields are global, not category-aware, so a criminal
defense call gets asked to fill `insurance_carrier` and an injury call gets
asked for `in_custody`. Retell's extraction quality is known to degrade as the
field list grows, and section 4 already warns that a missing/mismatched field
silently yields `null`. Going from 15 to 29 fields is a real risk to the fields
that currently work.

**Option B — extract category-specific fields in the backend with Gemini.
(Recommended.)** Keep Retell's extraction list as-is for universal fields. Add a
second Gemini pass in `classify.py` that, given the transcript and the already-
known category, fills only that category's fields against a category-specific
JSON schema.

Option B wins because the plumbing already exists and is proven: constrained
response schemas, retry-on-429, confidence gating, off-taxonomy rejection, the
`_manual_edits` guard that stops a redelivery from overwriting staff
corrections, and background execution that never delays the webhook. It's the
same shape as `classify_subcategory`, with a wider schema. It also keeps Retell
config stable and makes the fields re-runnable over historical calls.

Cost: one extra Gemini call per completed case, and it inherits Gemini as a
dependency — which is why fixing Gemini is Phase 0.

## 5. Proposed fields

Two tiers, and the distinction matters:

- **Tier 1 (§5a)** — facts the prompt *already asks for* but that have nowhere
  to go. Backend-only change; no prompt edit needed.
- **Tier 2 (§5b)** — basic facts **nobody asks today**. These need a prompt
  change *and* a field. This is the bigger quality win: today the agent simply
  never learns them.

All columns are appended to the `_NEW_COLUMNS` migration list in
`db.py:150-168`; the existing ALTER TABLE loop handles this safely on the live
database. All nullable. Booleans stay `INTEGER` to match the existing
convention (`injured`, `police_report_filed`) and must be genuinely tri-state —
`null` = never asked, which is the signal the completeness check reads. Note
that the current webhook coerces booleans with `int(bool(...))`
(`webhooks.py:136-139`), collapsing "unknown" into "no". The new fields must
not repeat that.

### 5a. Tier 1 — asked today, nowhere to store

| Column | Type | Category |
|---|---|---|
| `police_report_number` | TEXT | personal_injury |
| `insurance_carrier` | TEXT | personal_injury, medical_product |
| `reported_internally` | INTEGER | workplace_employment |
| `reported_date` | TEXT | workplace_employment |
| `still_employed` | INTEGER | workplace_employment |
| `workers_comp_filed` | INTEGER | workplace_employment |
| `children_involved` | INTEGER | family_law |
| `charges` | TEXT | criminal_defense |
| `in_custody` | INTEGER | criminal_defense |
| `immigration_status` | TEXT | immigration |
| `notice_type` | TEXT | real_estate_housing |
| `claim_filed` | INTEGER | estate_disability |
| `decedent_name` | TEXT | estate_disability |

### 5b. Tier 2 — basic questions missing from the prompt entirely

**Injury detail (personal_injury, medical_product).** The largest hole in the
whole intake. Today the agent records injury as a single yes/no (`injured`). It
never asks *what* was hurt, *how badly*, or *what treatment followed* — the
facts that determine whether a personal injury case is worth anything.

| Column | Type | Question to add |
|---|---|---|
| `body_parts_injured` | TEXT | "Which part of your body was hurt?" |
| `treatment_type` | TEXT | none / clinic / ER / hospital admitted / ongoing care |
| `treatment_provider` | TEXT | Name of the clinic, hospital, or doctor |
| `ambulance_called` | INTEGER | Was an ambulance called to the scene |
| `ongoing_symptoms` | INTEGER | Still in pain or still treating today |
| `work_missed` | TEXT | Any time missed from work, and roughly how much |
| `witnesses` | TEXT | Anyone who saw it happen |
| `vehicle_info` | TEXT | Vehicle / plate / registration of the other party |

**Per-category basics.**

| Column | Type | Category | Question to add |
|---|---|---|---|
| `product_name` | TEXT | medical_product | Name of the drug, device, or product |
| `job_title` | TEXT | workplace_employment | Their role / job title |
| `employment_length` | TEXT | workplace_employment | How long they worked there |
| `documentation_exists` | INTEGER | workplace_employment | Emails, texts, or written HR complaint |
| `children_count` | TEXT | family_law | How many children, and their ages |
| `court_name` | TEXT | criminal_defense | Which court or county |
| `bail_status` | TEXT | criminal_defense | Released, bonded out, or held |
| `country_of_origin` | TEXT | immigration | Country of origin |
| `detained` | INTEGER | immigration | Currently detained by ICE |
| `monthly_rent` | TEXT | real_estate_housing | Monthly rent amount |
| `lease_type` | TEXT | real_estate_housing | Written lease or verbal agreement |
| `contract_written` | INTEGER | business_contract | Was the contract in writing |
| `amount_in_dispute` | TEXT | business_contract | Rough dollar amount at stake |
| `will_exists` | INTEGER | estate_disability | Is there a will |

`witnesses` is shared by personal_injury and workplace_employment; the rest are
single-category.

Total: 13 Tier 1 + 22 Tier 2 = **35 new columns**. That count is itself the
decisive argument for Option B — configuring 35 additional global Retell
extraction fields would almost certainly degrade the 15 that work today, whereas
a category-scoped Gemini schema only ever asks for the 8-12 relevant to the call
in hand.

### Note on call length

Tier 2 adds real questions to live calls. The injury block alone is up to 8 more
turns, and the current bicycle-accident call already ran long on name and phone
confirmation. Mitigation: mark each field **must-ask** or **ask-if-natural** in
the completeness spec, and only gate the closing script on the must-ask set.
Suggested must-ask for personal_injury: `body_parts_injured`, `treatment_type`,
`ongoing_symptoms`. The rest are captured if the conversation allows and left
null otherwise — which the completeness report will show honestly rather than
hiding.

## 6. Phases

**Phase 0 — unblock Gemini (prerequisite).**
Redeploy `main` to Railway so `last_error` is present, re-run
`POST /debug/classify/<call_id>`, and fix whatever it names (quota, bad key,
model access). Nothing category-aware works until this does. Also turn off
`DEBUG_ENDPOINTS=1`, which is currently live in production and exposes full
transcripts and `/debug/purge` unauthenticated.

**Phase 1 — measurement first.**
Add `app/completeness.py` with the per-category required-fields spec, compute
`missing_fields` on the existing 16 fields, expose `/completeness-report`, and
show the gap in the dashboard. This is deliberately before any new field: it
establishes the baseline number we're trying to move, so Phase 3 can be proven
rather than assumed.

**Phase 2 — schema.**
Add the 35 columns (§5a + §5b) to the migration list, to `_UPDATABLE_COLUMNS`,
and to `RecordFieldsUpdate` in `schemas.py` so staff can correct them. Render
them in `CaseDetail.jsx`, grouped by category so a criminal case doesn't show
empty injury fields.

**Phase 3 — extraction.**
Extend `classify.py` with `extract_details(category, transcript, case_summary)`:
one Gemini call, category-specific response schema, confidence-gated, writing
only fields it's confident about and only where staff haven't already edited.
Wire it into `classify_and_store`.

**Phase 4 — prompt.**
Four changes to `agent-prompt-latest.txt`:

1. Add the §5b injury block to the personal_injury / medical_product
   follow-ups — body part, treatment type and provider, ambulance, ongoing
   symptoms, work missed, witnesses. This is new question content, not
   relabeling.
2. Add the per-category basics from §5b to their respective sections.
3. Split the defendant's insurance carrier out of the core representation
   question, which today conflates "have you spoken to an insurer" with "who
   insures the other side."
4. Name the target field on each follow-up line, the way existing lines say
   "capture as opposing_party," and add a pre-close check that the must-ask
   fields were actually covered before the closing script runs.

Verify with `TEST-SCENARIOS.html`, which is built to exercise exactly these
questions (see §9).

**Phase 5 — backfill and regression tests.**
Re-run extraction over stored transcripts to populate the new fields on existing
cases, then build the replay fixtures from `test-scenarios.md`.

## 7. Decisions I need from you

1. **Option A or B for extraction?** I recommend B (backend Gemini). A is less
   code but risks the extraction that currently works.
2. **Jurisdiction:** should a non-US matter route to `out_of_scope_calls`, or
   land in `cases` with a flag for staff to judge? This changes agent behavior
   mid-call, so it's your call, not a technical one.
3. **Field list:** anything in section 5 that the attorneys don't care about, or
   anything obviously missing? Worth 10 minutes with whoever works the cases —
   the whole plan keys off this list being right.
4. **Blocking vs advisory completeness:** should an incomplete case still land
   in `cases`, or divert to `partial_calls`? I'd keep it in `cases` with a
   visible warning — diverting risks burying a real client over one missing
   field.

## 8. Scope note

Phases 0-2 are safe and additive. Phase 3 changes what gets written to records
automatically, and Phase 4 changes live call behavior — both should be verified
against test calls before they touch production traffic.

## 9. Test material — `TEST-SCENARIOS.html`

Open it in a browser (it's self-contained; it also works on a phone while you're
on the call, and prints cleanly). Ten scenarios, one per practice area plus a
jurisdiction edge case.

Each card gives you a caller to play: an identity to read aloud, an opening
line, a short list of facts to **volunteer**, and a longer list to **withhold
until Maya asks**. The withheld list is the actual instrument — every fact in it
maps to a question from §5b. If Maya never asks, that fact never reaches the
record, and you've measured the gap directly rather than inferring it.

Each card ends with a checkbox list of the fields that should have landed.
Fields tagged `new` don't exist yet, so they will fail until Phases 2-3 ship —
that's the expected baseline, not a bug in the sheet. Progress persists in the
browser, so you can work through the suite across several sittings.

Two details deliberately built in:

- **Name traps.** Every persona has a name that a phone line mangles —
  hyphenated, two given names, a long surname, an ambiguous surname order.
  This exercises the spell-back rule at `agent-prompt-latest.txt:302-307`, which
  exists because a mis-heard name locks a caller out of their own case.
- **EDGE-10 replays the real 2026-08-03 call** — the Tamil Nadu bicycle
  accident — so you can confirm current jurisdiction behavior before deciding
  question 2 in §7.

Re-run the suite after Phase 4. The same sheet, scored twice, is the
before-and-after evidence that the prompt changes actually worked.
