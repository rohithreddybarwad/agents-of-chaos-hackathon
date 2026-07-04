"""Shared pytest fixtures: isolated DB per test module."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def fresh_app(tmp_path, monkeypatch):
    """Reload the app modules against a fresh, isolated SQLite DB."""
    db_path = tmp_path / "test_checkins.db"
    monkeypatch.setenv("MIRROR_DB_PATH", str(db_path))
    # A dummy key so client construction doesn't fail during import-time paths.
    monkeypatch.setenv("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", "test-key"))

    import config
    importlib.reload(config)
    import prompts_loader
    importlib.reload(prompts_loader)
    import claude
    importlib.reload(claude)
    import db as db_module
    importlib.reload(db_module)
    import main
    importlib.reload(main)

    from fastapi.testclient import TestClient

    db_module.init_db()
    with TestClient(main.app) as client:
        yield client, main, db_module, claude
