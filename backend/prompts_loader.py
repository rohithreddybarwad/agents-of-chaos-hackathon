"""Loads the exact system prompts verbatim from /prompts markdown files.

The prompt files wrap each prompt in a fenced ``` code block. We extract the
fenced block whose contents contain a known marker so the prompt text used at
runtime is exactly the text committed in /prompts (single source of truth) -
per AGENTS.md, these must be used verbatim and never rewritten.
"""
from __future__ import annotations

from config import CHECKIN_PROMPT_FILE, ONBOARDING_PROMPT_FILE


def _extract_fenced_block(markdown: str, marker: str) -> str:
    blocks: list[str] = []
    current: list[str] | None = None
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("\n".join(current))
                current = None
            continue
        if current is not None:
            current.append(line)
    for block in blocks:
        if marker in block:
            return block.strip()
    raise ValueError(f"Could not find a fenced block containing marker: {marker!r}")


def load_onboarding_system_prompt() -> str:
    md = ONBOARDING_PROMPT_FILE.read_text(encoding="utf-8")
    return _extract_fenced_block(md, "You are the onboarding step")


def load_checkin_system_prompt() -> str:
    md = CHECKIN_PROMPT_FILE.read_text(encoding="utf-8")
    return _extract_fenced_block(md, 'You are "The Mirror')
