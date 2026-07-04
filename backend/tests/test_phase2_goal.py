"""Phase 2: POST /goal two-turn onboarding flow.

Turn 1 returns a plain-text clarifying question; turn 2 (with the answer)
returns valid parsed JSON with all three fields and persists it.
"""
from __future__ import annotations

import json

from fakes import FakeClient
from prompts_loader import load_onboarding_system_prompt


def test_goal_two_turn_flow(fresh_app, monkeypatch):
    client, _main, db_module, claude = fresh_app

    question = "What's the first concrete thing that has to happen for this to be moving?"
    goal_json = json.dumps(
        {
            "goal_text": "Launch my online sneaker reselling side business",
            "success_signal": "First pair listed for sale on a marketplace",
            "review_cadence": "daily",
        }
    )
    fake = FakeClient([question, goal_json])
    monkeypatch.setattr(claude, "_get_client", lambda: fake)

    # Turn 1: only the raw goal -> plain-text question.
    r1 = client.post("/goal", json={"raw_goal_text": "I want to start reselling sneakers"})
    assert r1.status_code == 200
    assert r1.json() == {"clarifying_question": question}

    call1 = fake.messages.calls[0]
    assert call1["system"] == load_onboarding_system_prompt()
    assert call1["messages"] == [
        {"role": "user", "content": "I want to start reselling sneakers"}
    ]

    # Turn 2: raw goal + question + answer -> parsed JSON, persisted.
    r2 = client.post(
        "/goal",
        json={
            "raw_goal_text": "I want to start reselling sneakers",
            "clarifying_question": question,
            "clarifying_answer": "When I have my first pair listed for sale",
        },
    )
    assert r2.status_code == 200
    body = r2.json()
    assert set(body.keys()) == {"goal_text", "success_signal", "review_cadence"}
    assert body["success_signal"] == "First pair listed for sale on a marketplace"

    # The full 3-message exchange was sent on turn 2.
    call2 = fake.messages.calls[1]
    assert [m["role"] for m in call2["messages"]] == ["user", "assistant", "user"]
    assert call2["messages"][1]["content"] == question
    assert call2["messages"][2]["content"] == "When I have my first pair listed for sale"

    # Goal persisted and readable via /history.
    hist_goal = db_module.get_goal()
    assert hist_goal["success_signal"] == "First pair listed for sale on a marketplace"


def test_goal_turn2_requires_question(fresh_app):
    client, _main, _db, _claude = fresh_app
    r = client.post(
        "/goal",
        json={"raw_goal_text": "x", "clarifying_answer": "y"},
    )
    assert r.status_code == 400
