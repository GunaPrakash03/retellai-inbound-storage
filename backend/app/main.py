import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import get_case, list_cases, update_status
from .schemas import StatusUpdate
from .webhooks import router as webhook_router

app = FastAPI(title="Retell Intake Backend")
app.state.retell_api_key = os.getenv("RETELL_API_KEY", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/cases")
def get_cases(limit: int = 50, category: str | None = None, status: str | None = None):
    return list_cases(limit=limit, category=category, status=status)


@app.get("/cases/{call_id}")
def get_case_detail(call_id: str):
    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return row


@app.patch("/cases/{call_id}")
def patch_case_status(call_id: str, body: StatusUpdate):
    row = get_case(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    update_status(call_id, body.status)
    return get_case(call_id)
