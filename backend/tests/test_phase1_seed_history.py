"""Phase 1: fresh boot seeds 5 rows + goal; GET /history returns them ordered."""
from __future__ import annotations


def test_history_returns_five_seeded_rows_and_goal(fresh_app):
    client, _main, _db, _claude = fresh_app

    resp = client.get("/history")
    assert resp.status_code == 200
    data = resp.json()

    # Goal is seeded from the goal object in seed_checkins.json.
    goal = data["goal"]
    assert goal["goal_text"] == "Launch my online sneaker reselling side business"
    assert goal["success_signal"] == "First pair listed for sale"
    assert goal["review_cadence"] == "daily"

    checkins = data["checkins"]
    assert len(checkins) == 5

    # Ordered oldest to newest.
    dates = [c["date"] for c in checkins]
    assert dates == sorted(dates)
    assert dates[0] == "2026-06-29"
    assert dates[-1] == "2026-07-03"

    # Days 4 and 5 are pattern-detected; days 1-3 are not.
    assert [c["pattern_detected"] for c in checkins] == [False, False, False, True, True]
    assert checkins[3]["pattern_description"]
    assert checkins[4]["pattern_description"]


def test_seed_is_idempotent(fresh_app):
    client, _main, db_module, _claude = fresh_app
    db_module.seed_if_empty()
    db_module.seed_if_empty()
    resp = client.get("/history")
    assert len(resp.json()["checkins"]) == 5
