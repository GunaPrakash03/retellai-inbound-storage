# Implementation Plan — Receptionist-Style Call Routing & Transfers

Turning Maya from "intake-only" into something closer to a real
receptionist: recognizing returning callers, answering case-status
questions, and transferring to the right person.

Status: **Phases 0–2 code complete.** Phase 0 is committed. Phases 1
and 2 — data layer, case lookup with auth / rate limits / audit — are
built and tested but **not yet committed**. Two non-code steps remain
before Phase 4: registering the lookup function on the Retell agent
(dashboard task), and Phase 3 (Twilio), which stays the critical path.

D1–D5 in [§7](#7-decisions) were settled in the course of building
Phase 1 and are recorded there. **D6, D7 and D8 are still open** — D7 in
particular has no owner, and without one the status-lookup feature
degrades into reading stale dates to callers.

---

## 1. Goal

Today Maya treats every call as a brand-new intake. The target behavior:

- **First-time caller** → full intake (unchanged)
- **Returning caller, same matter, wants their attorney** → transfer, or take a message
- **Returning caller, same matter, wants a status update** → look up case by number, read back recorded facts
- **Returning caller, new matter** → full intake
- **Asks for a person by name** → transfer, or take a message
- **Billing / scheduling** → transfer to that department
- **Emergency / nonsensical / evasive / disconnected** → unchanged

---

## 2. Current state

Re-checked against the codebase on 2026-07-31, after Phase 1.

| Capability | State |
|---|---|
| Caller-ID lookup at call start | **Built** — `find_caller_history` now searches all six buckets; the inbound webhook returns `caller_known`, `previous_case_category`, `previous_case_summary` |
| Agent using those variables | **Not built** — the prompt still never references them; every caller is greeted identically. This is Phase 4 |
| Assigned attorney per case | **Built** — `assigned_to` column, editable from the case detail view |
| Staff directory | **Built** — `staff` table, CRUD endpoints, dashboard management view |
| Caller-friendly case number | **Built** — 6-digit `case_number`, allocated on first save, backfilled onto older records |
| Court-status / hearing tracking | **Built** — `court_status`, `next_hearing_date`, `court_status_updated`; staff edit these from the dashboard |
| Message taking | **Built** — `messages` table, endpoints, and a dashboard view. Nothing writes to it yet; the agent can't take messages until Phase 4 |
| Mid-call case lookup | **Built** — `POST /case-lookup` with auth (Retell signature or shared key), rate limiting, and an audit log; accepts Retell's custom-function payload shape. The only step left is registering it on the agent in the Retell dashboard |
| Call transfer | **Not built** — no transfer tool on the agent, and still blocked on a real phone number |

---

## 3. Blockers found during review

These are the things that make the original 4-item dependency list
insufficient. Each is verified, not assumed. **3.2 and 3.3 remain** and
both need Twilio; 3.5 is half-done. Everything else is resolved. 3.7 was
found later, while testing Phase 1.

### 3.1 Caller lookup only searches the `cases` table — **fixed**

`find_caller_history` queried `FROM cases` only. A caller whose first
call ended as a partial, or who was an emergency escalation, came back
as `caller_known = false` and got treated as brand new.

At the time, 6 of 24 records lived outside `cases`. The failure was
silent — the agent just ran a normal intake instead of erroring, so
nobody would have noticed it was broken.

**Fixed:** `find_caller_history` now unions all six bucket tables, most
recent first.

### 3.2 `from_number` is NULL on every record (0 / 24) — **still open**

The whole `caller_known` mechanism keys on caller ID. Retell's browser
test calls don't carry one — only real phone calls do.

**Consequence:** no returning-caller behavior can be tested until a real
phone number is connected.

### 3.3 Transfers require a real phone number — **still open**

Retell's transfer tool works on phone calls only, not web calls.
Combined with 3.2, **the entire transfer half of this plan is blocked on
Twilio.**

### 3.4 "Take a message" has nowhere to go — **fixed**

The routing plan says "take a message and promise a callback" on the
failure path of *every* transfer branch — the path that gets hit most
often in practice — but no message storage exists. This is a missing
5th dependency.

**Fixed:** `messages` table, endpoints, and a dashboard view with an
undelivered count in the nav. Note that nothing *writes* to it yet —
the agent gains that ability in Phase 4.

### 3.5 A case-number lookup can't use the inbound webhook — **built; registration pending**

The inbound webhook fires once, at call start, *before the caller has
said anything*. A case-number lookup has to happen mid-conversation,
after the caller reads the number out.

**This needs a different mechanism:** a Retell *custom function* (an API
the agent can call during a live call). Its exact configuration must be
confirmed against Retell's docs before Phase 2 is scoped.

**Addressed:** `POST /case-lookup` exists for exactly this, and the
custom-function contract is now confirmed against Retell's docs (see
Phase 2). The endpoint accepts both of Retell's payload modes and is
authenticated, rate-limited, and audited. The only remaining step is
registering it on the agent — a Retell-dashboard task, not code.

### 3.6 The word "status" is already taken — **fixed**

`status` already exists as the triage state (`new` / `reviewed` /
`contacted` / `closed`). Court status is a different concept. Two
meanings of "status" on one record will confuse both staff and the agent
— the new fields need distinct names (`court_status`,
`next_hearing_date`).

**Fixed:** the court fields are named `court_status`,
`next_hearing_date` and `court_status_updated`, and the dashboard shows
them under a separate "Court status" heading from the triage dropdown.

### 3.7 Migration ordering broke startup on the existing DB — **fixed**

Found while testing Phase 1, not during the original review. The new
`case_number` index was created inside the `CREATE TABLE` template,
which runs *before* the `ALTER TABLE` migration. On a fresh database
that works. On any existing deployment the table already exists, so
`CREATE TABLE IF NOT EXISTS` is a no-op, the column isn't there yet, and
startup dies with `no such column: case_number`.

The app would not have booted against the production database. Index
creation now runs after the column migration, with a regression test
that starts the app against a legacy-shaped DB.

---

## 4. Sequencing

```
Phase 0  Bug fixes                     ✅ done, committed
Phase 1  Data layer                    ✅ done, uncommitted
Phase 2  Mid-call case lookup          ◐  code done (auth, limits, audit); Retell registration left
Phase 3  Twilio phone number           ◻  not started — an account + number, not code
Phase 4  Transfers + prompt rewrite    ◻  blocked on Phase 3
```

All the code that can be written without a phone number has been.
What's left is configuration and external setup: registering the custom
function on the Retell agent, and **Phase 3, the critical path** — until
a real number exists, neither transfers nor returning-caller recognition
can be tested at all, and Phase 4 can't start.

---

## 5. Phase detail

### Phase 0 — Bug fixes ✅ complete (committed)

- [x] **Fix caller lookup scope** — `find_caller_history` searches all
      bucket tables instead of only `cases` (§3.1)
- [x] **Fix paraphrase misrouting** — the agent doesn't always say
      closing lines verbatim, so exact-phrase matching fails. Two of
      nine recent calls misrouted this way (~22%); one junk call landed
      in the attorney queue. Broadened `_OUTCOME_PHRASES` in
      `backend/app/validators.py` to match several distinctive
      fragments per ending rather than one exact sentence.
- [x] **Decide handling for out-of-scope callers** — resolved as a 6th
      bucket, `out_of_scope_calls` (D5).

### Phase 1 — Data layer ✅ complete (built, tested, uncommitted)

**Schema additions** to all six bucket tables:

| Column | Type | Purpose |
|---|---|---|
| `case_number` | TEXT | Short, speakable ID given to the caller (see D1) |
| `assigned_to` | TEXT | Staff member handling this case |
| `court_status` | TEXT | Free-text current court status |
| `next_hearing_date` | TEXT | Next scheduled hearing, if any |
| `court_status_updated` | TEXT | When court status was last touched — needed to warn about staleness (§7 D4). Named this rather than `status_updated_at` to keep it clearly distinct from triage `status` (§3.6) |

**New table — `staff`:**

| Column | Purpose |
|---|---|
| `id`, `name` | Who they are |
| `role` | Attorney / paralegal / billing / scheduling |
| `phone`, `extension` | Transfer destination |
| `active` | Soft-disable without deleting |

**New table — `messages`:**

| Column | Purpose |
|---|---|
| `id`, `call_id`, `case_number` | What call/case it relates to |
| `caller_name`, `callback_phone` | Who to call back |
| `message_text` | What they said |
| `for_staff_id` | Who it's for — joined to `staff.name` on read |
| `created_at`, `delivered` | Follow-up tracking |

**Tasks:**

- [x] Add the five columns, with an in-place migration for the existing
      production DB — see §3.7 for the ordering bug this surfaced
- [x] Generate `case_number` on first save for every new case, and keep
      it stable across webhook redeliveries (the caller may already have
      written it down)
- [x] Backfill `case_number` onto records that predate it, so every case
      has a number staff can read out. Idempotent; never reissues
- [x] Create `staff` and `messages` tables
- [x] CRUD endpoints for staff
- [x] Endpoint to create/list messages, and mark them delivered
- [x] Endpoint to set `court_status` / `next_hearing_date` on a case
- [x] Frontend: show case number, assigned staff, and court status on
      the case detail view, with a staleness warning past 14 days
- [x] Frontend: a messages view
- [x] Frontend: staff directory management (D2)
- [x] Frontend: sidebar nav with per-bucket counts and an undelivered
      message count

**Deliberately excluded from the webhook's updatable columns:**
`case_number`, `assigned_to`, `court_status`, `next_hearing_date`,
`court_status_updated`. A redelivered webhook must not wipe an attorney
assignment or a hearing date a human entered.

### Phase 2 — Mid-call case lookup ◐ code complete; registration left

- [x] Confirm how Retell custom functions work. From Retell's docs
      ([custom-function guide](https://docs.retellai.com/build/single-multi-prompt/custom-function)):
      Retell sends an HTTP request (method configurable; use POST) with
      body `{name, call, args}` — or just the bare args if
      "Payload: args only" is on. Requests carry the **same
      `X-Retell-Signature` HMAC header the post-call webhook already
      verifies**, and static custom headers can be added. Any 2xx
      response is stringified (capped at 15k chars) and handed to the
      LLM. Default timeout 2 minutes; **no retries** — on failure the
      agent gets the error text and continues per its prompt.
- [x] Build a lookup endpoint: case number + name check (D3) →
      returns `court_status`, `next_hearing_date`,
      `court_status_updated`, assigned staff name. `POST /case-lookup`,
      and it accepts **both** Retell payload modes as well as flat JSON,
      so registration works in either configuration
- [x] Return a clean "not found" the agent can handle gracefully. A
      wrong case number and a failed name check return an **identical**
      `{"found": false}` — distinguishing them would let someone probe
      which case numbers are real
- [x] **Auth**: a request must carry a valid `X-Retell-Signature`
      (verified with the same `RETELL_API_KEY` scheme as the webhook) or
      match the optional `CASE_LOOKUP_API_KEY` sent as an `X-API-Key`
      custom header. With neither env var set (local dev) the endpoint
      is open, like the rest of the API
- [x] **Rate limiting**: 20/min per client IP, 60/min globally, and —
      the one doing the real work — 30 *failed* lookups per IP per hour.
      Per-IP limits trust the platform proxy's `X-Forwarded-For`; the
      global cap is the floor if that assumption ever breaks. Limits are
      in-process, which is correct while the Procfile runs one worker
- [x] **Audit log**: every attempt (found / not_found / unauthorized)
      lands in `lookup_audit` with client IP, the live call's `call_id`,
      and what was asked; `GET /lookup-audit` lists it. Rate-limited
      requests are refused before touching case data and aren't audited
- [ ] **Register it on the Retell agent** — dashboard task, needs a
      human with Retell access. Settings: POST to
      `https://<backend>/case-lookup`; args schema
      `{case_number: string, caller_name: string}` (both required);
      either payload mode works; signature verification works as long as
      `RETELL_API_KEY` is set on the backend — optionally also set
      `CASE_LOOKUP_API_KEY` and add it as an `X-API-Key` custom header.
      After registering, verify a live web call: the signature scheme
      was confirmed from docs and tested with a synthetic header, not
      against real Retell custom-function traffic
- [ ] Prompt: tell the agent when to call the function and to read back
      **only** the returned fields — this lands with the Phase 4 rewrite

### Phase 3 — Twilio phone number ◻ not started — **the critical path**

- [ ] Follow the existing setup guide (`Retell AI Configuration.docx`,
      Part 2) to connect a real number
- [ ] Confirm `from_number` starts populating on real calls
- [ ] Re-run the existing test scenarios over a real phone line

### Phase 4 — Transfers + prompt rewrite ◻ blocked (needs 1, 2, 3)

- [ ] Add Retell's transfer tool to the agent
- [ ] Configure destinations dynamically from the staff directory
- [ ] Decide warm vs. cold transfer per call type (D6)
- [ ] Set ring duration and no-answer behavior → fall through to message
- [ ] Rewrite the prompt: returning-caller greeting, the same-issue /
      new-issue branch, case-number status flow, transfer triggers,
      message taking
- [ ] Update `_OUTCOME_PHRASES` for any new closing lines the rewrite
      introduces — **routing breaks silently if this is missed**

---

## 6. Testing

Existing scenarios in `backend/test-scenarios.md` must keep passing
unchanged — this work must not regress intake, safety, or bucket
routing.

### What was actually tested for Phases 1–2

88 checks against running servers on throwaway DBs, all passing:

- Phase 1 (45): staff CRUD, messages, assignment, court status, case
  lookup, case-number allocation and stability, regressions on every
  pre-existing route, and a migration test that boots the app against a
  legacy-shaped DB — columns, index, backfill, and idempotent restarts.
- Phase 2 (27): limiter unit tests; both Retell payload shapes plus
  numeric case numbers; audit rows for found / not_found / unauthorized
  with call_id and client IP; the per-IP limit tripping at exactly its
  threshold (and 429s staying out of the audit log); explicit-null staff
  updates; and a second server booted with keys set — wrong/missing
  credentials 401, shared key accepted, a real HMAC-signed
  `X-Retell-Signature` accepted, a stale signature rejected, dashboard
  routes unaffected.
- Bug-fix review pass (16): debug routes 404 unless `DEBUG_ENDPOINTS=1`;
  limiter key-map cleanup under IP churn; messages reject an unknown
  `for_staff_id`; a signed `call_analyzed` with no `call_id` returns 204
  instead of crashing; and — through a genuinely signed webhook for the
  first time — a completed intake landing in `cases` with a case number,
  an unsigned attempt still 401, and the inbound greeting returning
  empty strings (never nulls) for a partial-record caller.

The frontend builds clean.

Two caveats:

- The migration test uses a **synthetic** legacy DB — `backend/data/` is
  empty locally, so the real production DB was never exercised. The
  synthetic schema is older than production's, so it should be a safe
  proxy, but it isn't the real thing. Watch the first deploy.
- The dashboard was verified by build only, not clicked through in a
  browser.

### New call scenarios to add (all still pending — they need Phase 4)

| # | Scenario | Expected |
|---|---|---|
| 8 | Returning caller, same matter, asks for their attorney | Recognized; transfer attempted |
| 9 | Same as 8, attorney doesn't answer | Falls back to message; message is stored |
| 10 | Returning caller asks for status with a valid case number | Reads back only recorded facts |
| 11 | Status request, case number not found | Graceful fallback, offers transfer/message |
| 12 | Status request, identity check fails | Refuses to read details |
| 13 | Returning caller with a new, unrelated matter | Runs full intake |
| 14 | Caller asks for a person by name | Transfer attempted to that person |
| 15 | Billing question | Transfer to billing |
| 16 | Caller in `partial_calls` calls back | Recognized (regression test for §3.1) |

---

## 7. Decisions

D1–D5 were settled while building Phase 1. **D6–D8 are still open** and
all three block Phase 4.

- **D1 — Case number format.** → **Settled: 6-digit numeric**, e.g.
  `481920`. No letters — they get misheard over a phone (B/D/P/V, M/N).
  Random rather than sequential, so the number doesn't leak how many
  cases the office has taken and can't be guessed by counting up from
  someone else's.

- **D2 — Staff directory storage.** → **Settled: DB table with API and
  dashboard editing.** Office staff maintain it themselves; no redeploy
  to change a phone number.

- **D3 — Identity check for case-status lookups.** → **Settled: case
  number plus the name on file.** Partial/first-name matches are
  accepted, since callers say "Alex" when the file says "Alex Rivera".
  Requiring the call to come from the number on file was rejected as too
  brittle — it locks out anyone on a different phone.
  ⚠️ Still needs rate limiting before it's live (Phase 2).

- **D4 — Staleness handling.** → **Partly settled.** Every court-status
  edit stamps `court_status_updated`, the dashboard warns staff past 14
  days, and the lookup returns the timestamp so the agent *can* caveat.
  **Still to decide in Phase 4:** whether the agent always says "as of
  [date]", and whether status past some age is withheld entirely and
  routed to a human.

- **D5 — Out-of-scope callers.** → **Settled: own bucket**
  (`out_of_scope_calls`). Committed in Phase 0.

- **D6 — Warm vs. cold transfer.** Warm = the receiving person is
  briefed before the caller is connected. Cold = connected immediately.
  Per call type, or one rule for everything?
  → **Decision:** _open_

- **D7 — Who maintains court status?** Entering hearing updates is a new,
  ongoing human task that doesn't exist today. Attorney, paralegal, or
  someone doing manual docket checks? Without a real owner, the whole
  status-lookup feature degrades into reading stale data to callers.
  The fields and the dashboard editor now exist, which makes this the
  single most important open question — **the tooling is built and
  nobody is assigned to use it.**
  → **Decision:** _open_

- **D8 — Existing clients who never phoned in.** Someone onboarded in
  person isn't in the database, so they'd get a full new-client intake.
  Add a "have you worked with us before?" fallback, or accept this?
  → **Decision:** _open_

---

## 8. Risks

| Risk | Impact | Mitigation | State |
|---|---|---|---|
| Reading stale court status to a caller | A caller shows up on the wrong day for a hearing | D4 — caveat with last-updated date, or withhold when stale | Partly handled: timestamp stored, staff warned at 14 days. Agent behavior still to decide |
| Case details disclosed to the wrong person | Privacy / confidentiality breach | D3 — require a second identity factor | Name check, auth, rate limits, and audit log all in place |
| Prompt rewrite changes closing lines | Bucket routing silently breaks | Update `_OUTCOME_PHRASES` in the same change; re-run all test scenarios | Open — applies to Phase 4 |
| Nobody maintains the staff directory | Transfers dial dead numbers | D2 + a named owner | Tooling built; owner unnamed |
| Nobody maintains court status | Callers read stale dates | D7 | **Open — no owner** |
| Scope creep into a full case-management system | Never ships | Keep to read-only status lookup; staff enter updates elsewhere | Holding |

---

## 9. Known issues carried forward

Small things found during Phase 1, none blocking, all worth fixing
before or during Phase 4:

- **`assigned_to` stores a staff *name*, not an id.** Renaming someone
  in the directory silently orphans every case assigned to them. The
  dashboard papers over the symptom — a case whose assignee was
  deactivated or removed still shows that person, marked "(inactive)",
  rather than falsely reading "Unassigned" — but the underlying link is
  by string. Worth switching to `staff.id` when Phase 4 needs to resolve
  an assignee to a phone number anyway.
- ~~**`update_staff` ignores explicit nulls.**~~ **Fixed** — explicit
  nulls now clear `role` / `phone` / `extension`; `name` and `active`
  can't be nulled, so a null there is ignored rather than half-applied.
- **The messages table has no writer.** Endpoints and dashboard exist,
  but nothing creates a message until the agent can take one in Phase 4.
  Until then the Messages view is permanently empty, which may read as
  broken to staff.
- ~~**`/case-lookup` is unauthenticated.**~~ **Fixed** — requires a
  valid Retell signature or the `CASE_LOOKUP_API_KEY` header once either
  env var is set; plus rate limits and an audit trail. Remaining
  caveats: the rest of the dashboard API (staff, messages, court status)
  is still open, and the signature path hasn't been exercised by real
  Retell custom-function traffic yet — verify at registration time.
- **The audit log has no dashboard view and no retention policy.**
  `GET /lookup-audit` exists; nothing in the UI shows it, and rows
  accumulate forever. Fine at current volumes; revisit if lookups get
  real traffic.
