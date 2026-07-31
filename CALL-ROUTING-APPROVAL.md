# Call Routing & Transfer — Proposal for Approval

This is the proposed call-handling logic from `RECEPTIONIST-CALL-HANDLING.md`,
written as a plain bullet list for review and sign-off. Full context,
data-gap details, and open questions are in that document — this is just
the decision logic itself, isolated for approval.

## Proposed logic

- **First-time caller** — run the full intake exactly as today. No change.

- **Returning caller, same issue, wants to speak with their attorney directly**
  - Attempt to transfer the call to the attorney assigned to their case.
  - If the attorney doesn't pick up: take a message and promise a callback.

- **Returning caller, same issue, just wants a status update** (not
  necessarily a live person)
  - Ask the caller for their case number.
  - Look up the case's current recorded status.
  - If a status is on file (e.g., a hearing postponed to a new date):
    read back only the recorded facts — never speculate about outcome,
    next steps, or anything not explicitly on file.
  - If no status is on file, or the case number isn't found: say a
    status update isn't available right now, then offer to transfer to
    the attorney or take a message.

- **Returning caller, new and unrelated issue** — run the full intake as
  if they were a first-time caller.

- **Caller asks for a specific person by name**
  - Attempt to transfer to that person.
  - If unavailable: take a message and promise a callback.

- **Billing or scheduling question** — transfer to the relevant
  department.

- **Safety emergency, nonsensical, evasive, or disconnected call** — no
  change; handled exactly as today.

## Depends on (not yet built)

- A record of which attorney/staff member is assigned to each case.
- A staff directory mapping names/departments to phone numbers.
- A caller-friendly case number, given to callers at the end of their
  first call.
- A structured way for staff to record court-status updates (like a
  postponed hearing) after intake, so there's something to read back
  later.

## Approval

- [ ] Approved as-is
- [ ] Approved with changes (list below)
- [ ] Not approved

Comments:
