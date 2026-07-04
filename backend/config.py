"""Paths and configuration for The Mirror backend."""
from __future__ import annotations

import os
from pathlib import Path

# Repository root is one level up from /backend.
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def _resolve_asset_dir(name: str) -> Path:
    """Locate an asset dir either bundled in /backend (deploy) or at repo root (dev)."""
    bundled = BACKEND_DIR / name
    if bundled.is_dir():
        return bundled
    return REPO_ROOT / name


PROMPTS_DIR = _resolve_asset_dir("prompts")
DATA_DIR = _resolve_asset_dir("data")
DB_DIR = BACKEND_DIR / "db" if (BACKEND_DIR / "prompts").is_dir() else REPO_ROOT / "db"
FRONTEND_DIR = _resolve_asset_dir("frontend")

SEED_FILE = DATA_DIR / "seed_checkins.json"
ONBOARDING_PROMPT_FILE = PROMPTS_DIR / "onboarding_prompt.md"
CHECKIN_PROMPT_FILE = PROMPTS_DIR / "checkin_prompt.md"

# The single hardcoded demo user (no auth, no multi-user - see AGENTS.md).
DEMO_USER_ID = "demo_user"

# DB path is overridable so tests can use an isolated database.
DB_PATH = Path(os.environ.get("MIRROR_DB_PATH", str(DB_DIR / "checkins.db")))

# Fast/cheap current model - latency matters since /checkin runs live in the demo.
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-latest")
CLAUDE_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "1024"))
