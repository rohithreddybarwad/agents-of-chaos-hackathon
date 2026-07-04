"""SQLite persistence and startup seeding for The Mirror."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from config import DB_PATH, DEMO_USER_ID, SEED_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkins (
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

CREATE TABLE IF NOT EXISTS goals (
  user_id TEXT PRIMARY KEY,
  goal_text TEXT NOT NULL,
  success_signal TEXT NOT NULL,
  review_cadence TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not exist and seed the demo data on first boot."""
    with _connect() as conn:
        conn.executescript(SCHEMA)
    seed_if_empty()


def _row_to_checkin(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "date": row["date"],
        "goal_text": row["goal_text"],
        "checkin_text": row["checkin_text"],
        "agent_response": row["agent_response"],
        "pattern_detected": bool(row["pattern_detected"]),
        "pattern_description": row["pattern_description"] or "",
        "created_at": row["created_at"],
    }


def seed_if_empty(user_id: str = DEMO_USER_ID) -> None:
    """Insert the 5 seed rows + goal verbatim if the demo user has no check-ins yet."""
    with _connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM checkins WHERE user_id = ?", (user_id,)
        ).fetchone()["n"]
        if count > 0:
            return

        seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        goal = seed["goal"]
        conn.execute(
            """INSERT OR REPLACE INTO goals
               (user_id, goal_text, success_signal, review_cadence)
               VALUES (?, ?, ?, ?)""",
            (seed["user_id"], goal["goal_text"], goal["success_signal"], goal["review_cadence"]),
        )
        for c in seed["checkins"]:
            conn.execute(
                """INSERT INTO checkins
                   (id, user_id, date, goal_text, checkin_text, agent_response,
                    pattern_detected, pattern_description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    c["id"],
                    c["user_id"],
                    c["date"],
                    c["goal_text"],
                    c["checkin_text"],
                    c["agent_response"],
                    1 if c["pattern_detected"] else 0,
                    c.get("pattern_description", ""),
                    c["created_at"],
                ),
            )
        conn.commit()


def get_goal(user_id: str = DEMO_USER_ID) -> Optional[dict[str, str]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT goal_text, success_signal, review_cadence FROM goals WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "goal_text": row["goal_text"],
        "success_signal": row["success_signal"],
        "review_cadence": row["review_cadence"],
    }


def set_goal(
    goal_text: str,
    success_signal: str,
    review_cadence: str,
    user_id: str = DEMO_USER_ID,
) -> dict[str, str]:
    with _connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO goals
               (user_id, goal_text, success_signal, review_cadence)
               VALUES (?, ?, ?, ?)""",
            (user_id, goal_text, success_signal, review_cadence),
        )
        conn.commit()
    return {
        "goal_text": goal_text,
        "success_signal": success_signal,
        "review_cadence": review_cadence,
    }


def get_history(user_id: str = DEMO_USER_ID) -> list[dict[str, Any]]:
    """Full ordered check-in history (oldest to newest) for the user."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM checkins WHERE user_id = ? ORDER BY date ASC, id ASC",
            (user_id,),
        ).fetchall()
    return [_row_to_checkin(r) for r in rows]


def insert_checkin(
    *,
    date: str,
    goal_text: str,
    checkin_text: str,
    agent_response: str,
    pattern_detected: bool,
    pattern_description: str,
    user_id: str = DEMO_USER_ID,
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO checkins
               (user_id, date, goal_text, checkin_text, agent_response,
                pattern_detected, pattern_description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                date,
                goal_text,
                checkin_text,
                agent_response,
                1 if pattern_detected else 0,
                pattern_description,
                created_at,
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {
        "id": new_id,
        "user_id": user_id,
        "date": date,
        "goal_text": goal_text,
        "checkin_text": checkin_text,
        "agent_response": agent_response,
        "pattern_detected": pattern_detected,
        "pattern_description": pattern_description,
        "created_at": created_at,
    }
