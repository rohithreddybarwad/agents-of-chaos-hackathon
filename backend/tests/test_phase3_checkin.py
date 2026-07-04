"""Phase 3: POST /checkin wires checkin_prompt with the FULL history.

Verifies the response JSON, persistence, and - critically - that the prompt
sent to Claude contains all 5 prior seeded rows (the core premise).
"""
from __future__ import annotations

import json

from fakes import FakeClient
from prompts_loader import load_checkin_system_prompt


def test_checkin_sends_full_history_and_persists(fresh_app, monkeypatch):
    client, _main, db_module, claude = fresh_app

    result_json = json.dumps(
        {
            "response_text": "Six days now with the same 'tomorrow' - let's break it.",
            "pattern_detected": True,
            "pattern_description": "Deferred the photos/listing step every day 6/29-7/04.",
        }
    )
    fake = FakeClient([result_json])
    monkeypatch.setattr(claude, "_get_client", lambda: fake)

    resp = client.post("/checkin", json={"checkin_text": "Still didn't do it, tomorrow again."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pattern_detected"] is True
    assert body["agent_response"].startswith("Six days")
    assert body["pattern_description"]
    assert "id" in body and "date" in body

    # The single Claude call used the check-in system prompt verbatim.
    call = fake.messages.calls[0]
    assert call["system"] == load_checkin_system_prompt()

    # Sanity: the loaded system prompt is the real check-in prompt text.
    assert 'You are "The Mirror' in call["system"]

    # The user message must contain ALL 5 prior seeded check-ins, in order.
    user_message = call["messages"][0]["content"]
    seed_texts = [
        "finally picked the 5 pairs",  # day 1
        "Didn't get to the photos",     # day 2
        "my kid was sick",              # day 3
        "Same story today",             # day 4
        "actually just lazy",           # day 5
    ]
    positions = [user_message.find(t) for t in seed_texts]
    assert all(p != -1 for p in positions), positions
    assert positions == sorted(positions)  # oldest-to-newest order preserved
    assert user_message.count("They said:") == 5
    assert "Still didn't do it, tomorrow again." in user_message

    # The new row is persisted as the 6th check-in.
    history = db_module.get_history()
    assert len(history) == 6
    assert history[-1]["checkin_text"] == "Still didn't do it, tomorrow again."
    assert history[-1]["pattern_detected"] is True


def test_checkin_error_surfaces_as_502(fresh_app, monkeypatch):
    client, _main, _db, claude = fresh_app

    def boom():
        raise claude.ClaudeError("simulated API failure")

    monkeypatch.setattr(claude, "_get_client", boom)
    resp = client.post("/checkin", json={"checkin_text": "hello"})
    assert resp.status_code == 502
