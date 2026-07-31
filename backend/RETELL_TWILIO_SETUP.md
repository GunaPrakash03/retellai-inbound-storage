# Connecting a real phone number — Retell AI + Twilio

Everything in `RETELL_SETUP.md` covers the agent itself (prompt, webhooks,
Post-Call Data Extraction, bucket routing). This document covers the
separate piece: giving the intake line a real phone number callers can
dial, by connecting a Twilio number to Retell through SIP trunking.

You only need this if you want a real inbound phone number. Testing via
Retell's browser "Run Test" / web call doesn't require any of this.

## How it fits together

```
Caller dials Twilio number
        │
        ▼
Twilio Elastic SIP Trunk (origination → Retell)
        │
        ▼
Retell agent (the one configured in RETELL_SETUP.md)
        │
        ▼
Same webhook URLs already configured — no change needed here
```

The webhook config, system prompt, Post-Call Data Extraction fields, and
bucket routing all stay exactly as documented in `RETELL_SETUP.md`. Twilio
only changes how the call *reaches* the agent — everything downstream of
that is identical whether the call came from a browser test or a real
phone call.

## Prerequisites

- A Twilio account with a purchased phone number.
- The Retell agent already configured per `RETELL_SETUP.md`.

## 1. Create an Elastic SIP Trunk in Twilio

In the Twilio Console: **Elastic SIP Trunking → Trunks → Create new
Trunk**. Give it a name (e.g. `retell-intake`).

## 2. Set up Termination (outbound leg)

This is what lets Retell send calls out through your trunk.

1. Under the trunk's **Termination** settings, note the **Termination SIP
   URI** Twilio generates (a `*.pstn.twilio.com`-style address, localized
   to your region). You'll paste this into Retell in step 4.
2. Choose one authentication method for the trunk:
   - **IP whitelisting** — add Retell's SIP SBC CIDR block:
     `18.98.16.120/30`, or
   - **Username/password credentials** — create a Credential List with a
     username and password Retell will authenticate with.

Pick whichever your Twilio plan/region supports; both work.

## 3. Set up Origination (inbound leg)

This is what lets an inbound call to your Twilio number route to Retell.

Under the trunk's **Origination** settings, add an origination URI:

```
sip:sip.retellai.com
```

## 4. Assign your phone number to the trunk

Under the trunk's **Numbers** tab, add the Twilio number you want callers
to dial (buy a new one or move an existing one onto this trunk).

## 5. Import the number into Retell

In the Retell dashboard: **Phone Numbers → Import Number** (or the Import
Number API, if scripting this).

- Paste the **Termination SIP URI** from step 2.
- If you used username/password auth, enter those credentials.
- If you used IP whitelisting, no credentials are needed.

The number now shows up in your Retell dashboard's phone number list.

## 6. Assign the number to your agent

From the imported number's settings in Retell, assign it to the agent
configured in `RETELL_SETUP.md`. Inbound calls to this number now run that
agent, with the same webhook URLs, prompt, and Post-Call Data Extraction
already in place — nothing there needs to change for phone calls versus web
calls.

## Testing

Call the Twilio number from an actual phone. Run the same checks as any
other test call (see `test-scenarios.md` / `RETELL_SETUP.md` section 6):

```bash
curl -s https://<your-domain>/cases
curl -s https://<your-domain>/partial-calls
curl -s https://<your-domain>/unwanted-calls
curl -s https://<your-domain>/spam-calls
curl -s https://<your-domain>/emergency-flags
```

One thing to check that's specific to phone calls: `from_number` should now
be populated with the caller's real number (it was always `null` on web
test calls) — this is what `find_caller_history` in `app/db.py` uses to
recognize returning callers on the inbound webhook.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Twilio rejects outbound requests to Retell | The trunk's Termination security isn't set up — either whitelist `18.98.16.120/30` or add username/password credentials, matching what you entered when importing the number in Retell. |
| Import fails / number doesn't show up in Retell | Double-check the Termination SIP URI was copied exactly, and that credentials (if used) match a real Credential List on the trunk. |
| Inbound calls don't reach the agent at all | Confirm the trunk's Origination URI is exactly `sip:sip.retellai.com`, and that the phone number is actually assigned to this trunk (not left on Twilio's default voice webhook). |
| Caller ID looks wrong / not verified | Retell uses your trunk's verified caller ID — you need at least one number purchased directly through Twilio (not a ported number) in the same SIP trunk for this to apply correctly. |
| Everything downstream (buckets, fields, prompt behavior) is behaving differently on phone calls vs. web tests | It shouldn't — the webhook payloads and agent logic are identical either way. If they diverge, it's most likely audio-quality driven (phone codec vs. browser mic), not a config difference. |
