# Making Maya Handle Calls More Like a Human Receptionist

This is an analysis of what kinds of calls actually come into a law
office's general line, how a real receptionist would triage them, and
what would need to change so Maya does the same — including transferring
calls to a specific person when appropriate. This is a design document,
not a completed change; nothing here is implemented yet.

## The kinds of calls a receptionist actually handles

A general intake line gets more variety than just "new client with a
legal problem." A human receptionist typically sorts every call into one
of these buckets within the first few seconds:

| Call type | What a receptionist does today | What Maya does today |
|---|---|---|
| New potential client, first time calling | Runs intake, takes down the situation | This is the only case Maya currently handles |
| Existing client calling about their ongoing case | Recognizes them, pulls up their file, transfers to their attorney or paralegal, or takes a message | Not handled — see below |
| Caller asks for a specific person by name | Attempts to transfer; if unavailable, takes a message | Not handled at all — no transfer capability exists |
| Billing or scheduling question | Transfers to office manager / scheduling | Not handled |
| Wrong number, solicitor, robocall, prank | Politely ends the call | Handled — routes to `unwanted_calls` or `spam_calls` |
| Real emergency or safety situation | Tells caller to call 911 / escalates | Handled — routes to `emergency_flags` |
| Media, job applicant, vendor calls | Redirects to the right contact or takes a message | Not handled — would currently be forced through the legal-intake script, which doesn't fit |

The two gaps that matter most for feeling "more human" are the second and
third rows: **recognizing an existing caller** and **transferring to a
specific person**.

## What already exists for recognizing returning callers

This part is partially built already, but not finished. The backend's
inbound webhook (`/webhooks/retell/inbound`) already looks up the caller's
phone number against past cases the moment the call connects, and returns
three pieces of information to Retell before the agent even speaks:

- `caller_known` — true/false
- `previous_case_category` — what their last matter was about
- `previous_case_summary` — a one-line summary of it

**The gap:** the current agent script never actually uses these. Maya
greets every caller identically, whether it's their first call or their
tenth. This is the first thing worth fixing, and it doesn't require any
new infrastructure — only a prompt change to branch the opening based on
`caller_known`, something like:

> If `caller_known` is true, greet them by referencing their prior matter
> instead of starting cold: "Thanks for calling back — I have your
> previous call about [previous_case_category] on file. Is this about
> that same matter, or something new?" Then branch: if it's the same
> matter, move toward a transfer/message flow instead of a full intake;
> if it's something new, run the normal intake.

## What's needed for call transfer

Retell has a built-in **Transfer Call** capability that fits this need
directly:

- **Cold transfer** — immediately connects the caller to a destination
  and disconnects, no announcement.
- **Warm transfer** — Retell stays on the line, can leave a private
  briefing message the caller doesn't hear, and only bridges the call
  once a real person picks up (it detects voicemail/no-answer so a caller
  is never handed to a dead line).
- **Agentic warm transfer** — a specialized transfer step calls the
  destination first to check availability/screen, then decides whether
  to bridge or cancel.

The destination can be a fixed phone number, or a **variable substituted
at call time** — meaning the destination itself can be decided
dynamically per call (e.g., "whichever attorney this case is assigned
to"), not just one fixed forwarding number for everyone.

Retell doesn't decide on its own when to transfer — this is entirely
driven by instructions written into the agent's prompt (e.g., "if the
caller asks for a specific person by name, or if this is a returning
caller with an active case, use the transfer tool"). If the destination
doesn't answer within a configurable ring duration, that counts as
unanswered, and the prompt needs to define what happens next (take a
message, offer a callback, or fall back to Maya continuing normally).

## What's missing to make this actually work

Four real gaps need to be filled before this can be built, none of which
exist in the system today:

1. **No record of who's assigned to a case.** The database currently
   stores the caller's situation, but nothing about which attorney or
   staff member is handling it. Without this, there's no way to know
   *who* to transfer a returning caller to.
2. **No staff directory.** There's no list mapping attorney/staff names
   (or roles like "billing," "scheduling") to actual phone
   numbers/extensions that Retell could dial.
3. **No caller-friendly case number.** Cases are currently identified
   internally by Retell's own call ID (a long generated string), which a
   caller would never know or be able to read back over the phone. A
   short, spoken-friendly case number (e.g., a 5–6 digit number) would
   need to be generated and given to the caller at the end of their first
   call, so they have something to reference later.
4. **No structured court-status / hearing tracking.** Right now, intake
   captures a case's situation once, at the moment of the first call —
   there's no mechanism for staff to record status updates afterward
   (like a hearing being postponed to a new date) that Maya could then
   read back on a later call. This isn't something the voice agent
   creates on its own; it requires staff to actually enter these updates
   somewhere as the case progresses through court, and a structured place
   to store them (a real hearing-date field, not just the general-purpose
   `key_date_or_deadline` text field currently used at intake).

Until all four exist, transfer logic can really only support the simpler
cases — like "transfer anyone who asks for a specific named attorney" (if
given a static list of names → numbers) — not "transfer this returning
caller to *their* attorney specifically," and case-status lookups by case
number aren't possible at all yet.

## Proposed call-handling logic (for discussion)

```
Call connects
  │
  ├─ caller_known = false (first-time caller)
  │     → run full intake exactly as today
  │
  ├─ caller_known = true (returning caller)
  │     → greet referencing their prior matter, ask if it's the same issue
  │     ├─ Same issue, wants to speak with their attorney directly
  │     │     → attempt a transfer to the assigned attorney (needs #1 above)
  │     │     → if unavailable: take a message, promise a callback
  │     ├─ Same issue, just wants a status update (not necessarily a live person)
  │     │     → ask for their case number (needs #3 above)
  │     │     → look up the case's current recorded status (needs #4 above)
  │     │     ├─ Status is on file (e.g., hearing postponed to a new date)
  │     │     │     → read back only the recorded facts (date/status) —
  │     │     │       never speculate on outcome, next steps, or anything
  │     │     │       not explicitly recorded
  │     │     └─ No status on file / case number not found
  │     │           → say a status update isn't available right now,
  │     │             offer to transfer to the attorney or take a message
  │     └─ New, unrelated issue
  │           → run full intake as if new
  │
  ├─ Caller explicitly asks for a person by name
  │     → attempt a transfer to that person (needs #2 above)
  │     → if unavailable: take a message, promise a callback
  │
  ├─ Billing / scheduling / non-legal question
  │     → transfer to the relevant department (needs #2 above)
  │
  └─ Safety emergency / nonsensical / evasive / disconnected
        → unchanged, handled exactly as today
```

## Open questions before building this

- Should returning callers always be offered a transfer, or only once
  their case has moved past "new" status (implying an attorney is
  actually assigned and reachable)?
- What should Maya do if a transfer target doesn't pick up — take a
  full message, or fall back into doing a normal intake-style
  conversation about the update?
- Who maintains the staff directory (names → attorney/department →
  phone number) once it exists, and how does the assigned-attorney field
  get set for a case in the first place — manually by staff, or
  automatically based on case category?
- Does every attorney want warm transfer (briefed before the call
  connects) or is cold transfer acceptable for some call types (e.g.,
  billing questions)?
- Who is responsible for entering court-status updates (like a
  postponed hearing) into the system as a case moves forward — the
  attorney, a paralegal, someone doing manual data entry after checking
  the court docket? This is a new, ongoing task that doesn't exist today.
- How current does a status reading need to be? If a hearing is
  postponed and the record isn't updated for a few days, Maya would read
  back a stale date — is a "last updated on [date]" caveat read back to
  the caller good enough, or does this data need to be kept current in
  some other, more reliable way (e.g., synced from a court records
  system instead of manual entry)?
- Should case number lookups be available to any caller who provides one
  correctly, or should there be some additional identity check first
  (e.g., confirming the caller's name matches the one on file for that
  case), to avoid one caller learning details about someone else's case?
