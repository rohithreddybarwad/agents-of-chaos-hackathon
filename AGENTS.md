# AGENTS.md - The Mirror

> Guidance for Devin (and any AI coding agent) working in this repo.

## What we're building
The Mirror: a habit/accountability coach agent. A person states one real, big life goal. Each day they send a short text check-in. The agent holds the FULL history of past check-ins and reasons over all of it - not just today's message - to spot real, evidence-backed patterns (repeated excuses, drift from the stated goal) and reflect them back like a warm, forward-looking coach. It never diagnoses, never speculates about feelings or psychology - it only reflects observed behavior, with cited evidence.

**The demo is the product:** open the app pre-seeded with 5 days of a fake persona's check-ins (an escalating "I'll do it tomorrow" pattern for launching a jewelry side business). The feed shows days 1-3 with warm, no-pattern responses, then day 4 and day 5 visually flagged as pattern-detected (distinct border/color) with the agent naming the exact evidence. Then, live and unscripted, a judge or Rohith types a NEW check-in into the box and watches the agent reason over the full history in real time and respond - proving it's not scripted.

## Repository structure
```
/backend        FastAPI: POST /goal, POST /checkin, GET /history
/prompts        onboarding_prompt.md, checkin_prompt.md (the exact system prompts to use verbatim - do not rewrite them)
/data           seed_checkins.json (the exact seed data to insert on startup - do not regenerate it)
/frontend       React (or plain HTML+JS if faster) - goal banner, chat-style check-in feed, pattern-flagged cards visually distinct
/db             checkins.db (SQLite, created on startup)
/docs           this file
```

## Setup commands
- Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev` (or served as static files by FastAPI if plain HTML+JS)
- Env: copy `.env.example` to `.env`; needs only `ANTHROPIC_API_KEY`. No other keys, no OAuth, no third-party accounts.

## Database schema
Single SQLite table:
```sql
CREATE TABLE checkins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  date TEXT NOT NULL,
  goal_text TEXT NOT NULL,
  checkin_text TEXT NOT NULL,
  agent_response TEXT NOT NULL,
  pattern_detected BOOLEAN NOT NULL,
  pattern_description TEXT,
  created_at TEXT NOT NULL
);
```
Also store the goal itself (goal_text, success_signal, review_cadence) - either a separate one-row `goals` table keyed by user_id, or a small JSON/config file. Keep it simple; there is only ever one active goal for the one demo user.

## Endpoints
- `POST /goal` - body: `{ raw_goal_text, clarifying_answer?: string }`. First call (no `clarifying_answer`): call Claude with `onboarding_prompt` and only the raw goal, return the clarifying question as plain text. Second call (with `clarifying_answer`): call Claude with `onboarding_prompt` and the full 3-message exchange (raw goal, the question, the answer), parse the returned JSON `{goal_text, success_signal, review_cadence}`, persist it as the active goal, return it.
- `POST /checkin` - body: `{ checkin_text }`. Load the active goal + the FULL ordered history of past checkins for the user. Build the user message per the template in `/prompts/checkin_prompt.md` (goal fields + full history + today's check-in). Call Claude with `checkin_prompt` as the system prompt. Parse the returned JSON `{response_text, pattern_detected, pattern_description}`. Insert a new row into `checkins` with all fields. Return the parsed response plus the new row's id/date.
- `GET /history` - returns the full ordered list of checkin rows for the demo user (for the frontend feed), plus the active goal.

## Seeding
On backend startup, if the `checkins` table is empty for `user_id = "demo_user"`, insert the 5 rows from `/data/seed_checkins.json` exactly as given (do not call the LLM to regenerate them - they are pre-written and must load instantly). Also set the active goal from the `goal` object in that same file. This must happen automatically on boot with no manual step, so the frontend has the full pattern-catch story visible the instant it loads.

## Core design rules (do NOT violate)
- **Full history, every call.** `/checkin` must always pass the complete ordered check-in history to Claude, not just the latest message. This is the entire premise of the product - do not optimize this away by only sending recent turns.
- **The LLM decides pattern_detected, not code.** Do not add a keyword-matching or regex fallback to flag patterns - that defeats the premise. If the Claude call fails, show an error state, don't fake a result.
- **Exact prompts.** Use the system prompts in `/prompts/onboarding_prompt.md` and `/prompts/checkin_prompt.md` verbatim as given - they encode specific tone and JSON-output rules that the demo depends on.
- **No auth, no OAuth, no third-party accounts.** Single hardcoded demo user (`user_id = "demo_user"`). The only secret is `ANTHROPIC_API_KEY`.
- **Visually distinguish pattern-detected responses** in the frontend feed - different border/background color from normal responses - this is the single most important visual element of the demo.

## Non-goals (do NOT build)
- Do NOT build multi-user support, login, or signup.
- Do NOT build a goal-editing UI beyond the one-time onboarding flow.
- Do NOT build push notifications, reminders, or scheduling.
- Do NOT add any therapy/diagnosis language anywhere in the UI copy either - keep the product framing consistent with the prompts (coach, not therapist).

## Build order (lean MVP, solo builder + Devin)
1. Backend scaffold: FastAPI app, SQLite table, seed-on-startup logic loading `/data/seed_checkins.json` verbatim. Test: hitting `GET /history` right after a fresh boot returns the 5 seeded rows plus the goal, correctly ordered.
2. `/goal` endpoint: wire both turns of the onboarding flow to `onboarding_prompt.md` via the Anthropic API. Test: first call returns a plain-text question; second call (with an answer) returns valid parsed JSON with all three fields.
3. `/checkin` endpoint: wire to `checkin_prompt.md`, constructing the full-history user message per the template. Test: submitting a new check-in after the 5 seeded rows returns valid JSON, and manually verify the prompt sent to Claude actually contains all 5 prior rows (log it or assert on the request payload in a test).
4. Frontend: goal banner at top (goal_text + success_signal), chat-style feed rendering all history from `/history` in order, pattern-detected cards visually distinct, a check-in input box at the bottom that POSTs to `/checkin` and appends the new response to the feed live. Record a browser video showing the seeded pattern-catch on day 4/5 and then a new live check-in being answered.
5. Ship: deploy backend + frontend together (whichever of Vercel/Render/Fly is fastest - Render is usually simplest for a single FastAPI app serving static frontend files). Confirm the full flow works on the public URL: loads with seeded history visible, pattern cards distinct, new check-in works live. Record a final browser video.

## Verification (per phase)
Each phase must ship with a passing test named in its task, and for phases 4-5, a browser video recording of the feature working. Do not report "done" without both.

## Conventions
- Python: FastAPI, type hints, `pytest`. Use the official `anthropic` Python SDK for Claude calls.
- JS: React functional components, or plain HTML+JS with fetch() if that's faster to ship in the time remaining - Devin's call, optimize for finishing over polish.
- Keep API calls to Claude using a fast/cheap current model - latency matters since `/checkin` is called live during the demo.
- Commit per phase.
