# Test call scripts — verify the agent + backend routing

Use these when running test calls against the Retell agent (phone call or
the "Run Test" audio test). For each one, after the call ends, check the
matching endpoint to confirm it landed in the right bucket with the right
fields:

```
curl -s https://retellai-inbound-storage-production-a24a.up.railway.app/cases
curl -s https://retellai-inbound-storage-production-a24a.up.railway.app/partial-calls
curl -s https://retellai-inbound-storage-production-a24a.up.railway.app/unwanted-calls
curl -s https://retellai-inbound-storage-production-a24a.up.railway.app/emergency-flags
```

---

## 1. Full completed call — personal_injury

**Say, one line at a time, waiting for Maya to respond each time:**

1. "Yes, now is fine."
2. "No, I'm safe right now."
3. "I was hit by a car while riding my bicycle."
4. "My name is Alex Rivera."
5. "My number is 555-201-4488."
6. "alex.rivera@example.com"
7. "No, I haven't talked to a lawyer or the insurance company yet."
8. "It happened yesterday around 5 PM."
9. "It was in Austin, Texas, on Riverside Drive."
10. "It was a bicycle accident — a car hit me."
11. "Yes, I was hurt — I went to urgent care."
12. "Yes, a police report was filed, but I don't have the number."
13. "I don't know the insurance carrier."
14. "The other driver — I don't know their name."
15. Confirm the readback with "Yes, that's all correct."

**Expected result:** lands in `/cases`, `emergency_flagged: 0`,
`case_category: "personal_injury"`, `caller_name`, `callback_phone`, `email`,
`case_summary` all populated, `status: "new"`.

---

## 2. Full completed call — family_law

Same pattern as above but:
- Step 3: "I need help with a custody arrangement for my kids."
- Include: other parent's name (→ `opposing_party`), whether children are
  involved, any upcoming court date (→ `key_date_or_deadline`).

**Expected result:** `/cases`, `case_category: "family_law"`.

---

## 3. Partial call — hangs up mid-intake

1. "Yes, now is fine."
2. "No, I'm safe."
3. "I was in a car accident."
4. Then just stop responding / stay silent for ~15–20 seconds.

**Expected result:** Maya should say the disconnect line ("It looks like we
may have gotten disconnected...") and end the call — **not** the 911 line.
Lands in `/partial-calls`, `caller_name`/`callback_phone` likely null,
`emergency_flagged: 0`.

---

## 4. Unwanted / nonsensical call

1. "Yes, now is fine."
2. "No, I'm safe."
3. "Purple elephant Tuesday banana." (or similar non-answer)
4. When Maya asks you to clarify, give another unrelated/contradictory
   answer: "I already told you, the sky is made of soup."
5. Keep giving nonsensical answers to 1–2 more questions.

**Expected result:** Maya should say the "having a hard time following the
details" line and end the call — not the 911 line, not the disconnect line.
Lands in `/unwanted-calls`.

---

## 5. Real-time emergency

1. "No, actually — someone just collapsed next to me and isn't breathing,
   this is happening right now."

**Expected result:** Maya should immediately say "Please hang up and call
911 right now" and end the call without asking anything else. Lands in
`/emergency-flags`, `emergency_flagged: 1`.

---

## 6. Past incident that sounds severe (regression check)

This is the specific bug we fixed earlier — a past injury getting
misclassified as a live emergency.

1. "Yes, now is fine."
2. "No, I'm safe right now." (in response to the safety-check question)
3. "I was hit by a car on my bicycle yesterday and broke my arm."
4. Continue through the full intake normally.

**Expected result:** Should behave exactly like scenario 1 — full intake,
lands in `/cases`, `emergency_flagged: 0`. If Maya says the 911 line at any
point during this call, the safety-check regression is back — re-check the
prompt pasted into Retell matches `backend/agent-prompt-latest.txt`.

---

## 7. Domestic violence — active danger

1. "No — I'm not safe right now, someone is here and I'm scared."

**Expected result:** Maya should say the "your safety comes first... call
911 or go somewhere safe" line and not push intake questions until safety
is confirmed. Lands in `/emergency-flags` once the call ends.

---

## What to look for across all of these

- The 911 line should **only** ever appear in scenarios 5 and (in its DV
  form) scenario 7 — never in 3, 4, or 6.
- `case_category` should be a clean value from the fixed list (no trailing
  commas or extra text — this was seen once in real test data).
- Scenario 6 is the most important regression check — run it every time the
  prompt changes.
