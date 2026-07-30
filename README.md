# Retell Intake — Case Dashboard

Captures every Retell AI intake call (any legal case type — personal
injury, family law, criminal defense, immigration, employment, etc.) into a
FastAPI + SQLite backend, and reviews them in a React dashboard.

```
retell-intake/
├── backend/     FastAPI + SQLite — receives Retell webhooks, stores cases
└── frontend/    React (Vite) — dashboard to browse and triage cases
```

## Run the backend

```bash
cd backend
pip install --user -r requirements.txt   # add --break-system-packages if pip refuses (Debian/Ubuntu)
cp .env.example .env                      # then set RETELL_API_KEY to your real key
python3 -m uvicorn app.main:app --reload --port 8000
```

Backend docs (auto-generated): http://localhost:8000/docs

## Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Dashboard: http://localhost:5173

## Connect Retell to this backend

1. Expose the backend publicly for Retell to reach it: `ngrok http 8000`
2. Agent → **Webhook Settings** → `https://xxxx.ngrok.app/webhooks/retell`
3. Phone Number → **Inbound Webhook** (optional, greets returning callers) →
   `https://xxxx.ngrok.app/webhooks/retell/inbound`
4. Agent → **Prompt** → paste in `backend/agent-prompt.md`
5. Agent → **Post-Call Data Extraction** → add the fields listed in
   `backend/README.md` — the dashboard reads exactly those field names.

## What the dashboard shows

- A filterable list of every captured case (by category, by status)
- Per-case detail: all extracted fields, the recording (playable inline),
  the full transcript, and a status dropdown (`new → reviewed → contacted
  → closed`) that writes back to the database immediately

See `backend/README.md` for the full field-mapping table and webhook setup
details.
# retellai-inbound-storage
