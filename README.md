# The Mirror

A habit/accountability coach agent. You state one real, big life goal, then send a
short daily text check-in. The agent holds the **full** history of past check-ins and
reasons over all of it — not just today's message — to spot real, evidence-backed
patterns (repeated excuses, drift from the goal) and reflect them back like a warm,
forward-looking coach. It never diagnoses or speculates — it only reflects observed
behavior, with cited evidence.

See [AGENTS.md](AGENTS.md) for the full design spec.

## Stack
- **Backend:** FastAPI + SQLite, official `anthropic` SDK for Claude calls.
- **Frontend:** static HTML/CSS/JS served by FastAPI (single-service deploy).

## Run locally
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 — the app boots pre-seeded with 5 days of demo check-ins
(days 4 & 5 flagged as pattern-detected). Type a new check-in to see Claude reason
over the full history live.

Run the tests:
```bash
cd backend && source .venv/bin/activate && pytest
```

## Endpoints
- `GET /history` — full ordered check-in history + the active goal.
- `POST /goal` — two-turn onboarding: first call returns a clarifying question, second
  call (with the answer) returns and persists `{goal_text, success_signal, review_cadence}`.
- `POST /checkin` — `{checkin_text}`; sends the goal + full history + today's check-in to
  Claude and returns the new row `{..., agent_response, pattern_detected, pattern_description}`.

## Deploy (Render)
A [`render.yaml`](render.yaml) blueprint is included. Create a Render Blueprint from this
repo and set the `ANTHROPIC_API_KEY` environment variable in the dashboard. The single web
service serves both the API and the frontend.

## Configuration
- `ANTHROPIC_API_KEY` (required) — the only secret.
- `CLAUDE_MODEL` (optional, default `claude-haiku-4-5-20251001`).
- `MIRROR_DB_PATH` (optional, default `db/checkins.db`).
