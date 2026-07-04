"""Anthropic Claude calls for onboarding and check-in reasoning."""
from __future__ import annotations

import json
import os
from typing import Any

from anthropic import Anthropic

from config import CLAUDE_MAX_TOKENS, CLAUDE_MODEL
from prompts_loader import load_checkin_system_prompt, load_onboarding_system_prompt


class ClaudeError(RuntimeError):
    """Raised when the Claude call fails or returns unparseable output."""


_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ClaudeError("ANTHROPIC_API_KEY is not set")
        _client = Anthropic(api_key=api_key)
    return _client


def _text_from_response(message: Any) -> str:
    parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    return "".join(parts).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from the model output, tolerating stray code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def onboarding_question(raw_goal_text: str) -> str:
    """Turn 1: return the plain-text clarifying question."""
    try:
        message = _get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=load_onboarding_system_prompt(),
            messages=[{"role": "user", "content": raw_goal_text}],
        )
        return _text_from_response(message)
    except ClaudeError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any SDK/network error uniformly
        raise ClaudeError(f"Onboarding (turn 1) call failed: {exc}") from exc


def onboarding_goal(raw_goal_text: str, clarifying_question: str, clarifying_answer: str) -> dict[str, str]:
    """Turn 2: return the parsed {goal_text, success_signal, review_cadence}."""
    try:
        message = _get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=load_onboarding_system_prompt(),
            messages=[
                {"role": "user", "content": raw_goal_text},
                {"role": "assistant", "content": clarifying_question},
                {"role": "user", "content": clarifying_answer},
            ],
        )
        raw = _text_from_response(message)
    except Exception as exc:  # noqa: BLE001
        raise ClaudeError(f"Onboarding (turn 2) call failed: {exc}") from exc

    try:
        data = _parse_json_object(raw)
        return {
            "goal_text": data["goal_text"],
            "success_signal": data["success_signal"],
            "review_cadence": data["review_cadence"],
        }
    except (json.JSONDecodeError, KeyError) as exc:
        raise ClaudeError(f"Could not parse onboarding JSON from model: {raw!r}") from exc


def build_checkin_user_message(
    goal: dict[str, str],
    history: list[dict[str, Any]],
    today_date: str,
    today_checkin_text: str,
) -> str:
    """Build the user message per the template in /prompts/checkin_prompt.md."""
    lines = [
        f"GOAL: {goal['goal_text']}",
        f"SUCCESS SIGNAL: {goal['success_signal']}",
        f"REVIEW CADENCE: {goal['review_cadence']}",
        "",
        "PAST CHECK-INS (oldest to newest):",
    ]
    for row in history:
        lines.append(
            f'- [{row["date"]}] They said: "{row["checkin_text"]}" '
            f'| You responded: "{row["agent_response"]}"'
        )
    lines.append("")
    lines.append(f'TODAY\'S CHECK-IN ({today_date}): "{today_checkin_text}"')
    lines.append("")
    lines.append("Reason over the full history above, then respond per your instructions.")
    return "\n".join(lines)


def run_checkin(user_message: str) -> dict[str, Any]:
    """Call Claude with the check-in system prompt; return parsed JSON."""
    try:
        message = _get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=load_checkin_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
        )
        raw = _text_from_response(message)
    except Exception as exc:  # noqa: BLE001
        raise ClaudeError(f"Check-in call failed: {exc}") from exc

    try:
        data = _parse_json_object(raw)
        return {
            "response_text": data["response_text"],
            "pattern_detected": bool(data["pattern_detected"]),
            "pattern_description": data.get("pattern_description", "") or "",
        }
    except (json.JSONDecodeError, KeyError) as exc:
        raise ClaudeError(f"Could not parse check-in JSON from model: {raw!r}") from exc
