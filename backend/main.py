"""The Mirror - FastAPI backend.

Endpoints: POST /goal, POST /checkin, GET /history.
Serves the static frontend (if present) so the whole app deploys as one service.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import claude
import db
from config import DEMO_USER_ID, FRONTEND_DIR

logger = logging.getLogger("the_mirror")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="The Mirror", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GoalRequest(BaseModel):
    raw_goal_text: str
    clarifying_question: str | None = None
    clarifying_answer: str | None = None


class CheckinRequest(BaseModel):
    checkin_text: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/history")
@app.get("/api/history")
def history() -> dict[str, object]:
    return {
        "goal": db.get_goal(DEMO_USER_ID),
        "checkins": db.get_history(DEMO_USER_ID),
    }


@app.post("/goal")
@app.post("/api/goal")
def post_goal(req: GoalRequest):
    raw = (req.raw_goal_text or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="raw_goal_text is required")

    # Turn 1: no answer yet -> return the plain-text clarifying question.
    if not req.clarifying_answer:
        try:
            question = claude.onboarding_question(raw)
        except claude.ClaudeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"clarifying_question": question}

    # Turn 2: we have the answer -> produce and persist the concrete goal.
    if not req.clarifying_question:
        raise HTTPException(
            status_code=400,
            detail="clarifying_question is required on the second call",
        )
    try:
        goal = claude.onboarding_goal(raw, req.clarifying_question, req.clarifying_answer)
    except claude.ClaudeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    saved = db.set_goal(
        goal_text=goal["goal_text"],
        success_signal=goal["success_signal"],
        review_cadence=goal["review_cadence"],
        user_id=DEMO_USER_ID,
    )
    return saved


@app.post("/checkin")
@app.post("/api/checkin")
def post_checkin(req: CheckinRequest):
    text = (req.checkin_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="checkin_text is required")

    goal = db.get_goal(DEMO_USER_ID)
    if goal is None:
        raise HTTPException(status_code=400, detail="No active goal set")

    history_rows = db.get_history(DEMO_USER_ID)
    today = datetime.now(timezone.utc).date().isoformat()

    user_message = claude.build_checkin_user_message(goal, history_rows, today, text)
    logger.info("Check-in prompt sent to Claude (%d prior rows):\n%s", len(history_rows), user_message)

    try:
        result = claude.run_checkin(user_message)
    except claude.ClaudeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    row = db.insert_checkin(
        date=today,
        goal_text=goal["goal_text"],
        checkin_text=text,
        agent_response=result["response_text"],
        pattern_detected=result["pattern_detected"],
        pattern_description=result["pattern_description"],
        user_id=DEMO_USER_ID,
    )
    return row


# Serve the static frontend last so API routes take precedence.
if FRONTEND_DIR.is_dir() and (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
