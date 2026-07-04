"""Fake Anthropic client for deterministic endpoint tests.

Mocks only the SDK network boundary (messages.create) so tests exercise the
real system-prompt selection, message construction, JSON parsing, and
persistence wiring without a live API call.
"""
from __future__ import annotations

from typing import Any


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]


class FakeMessages:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Message:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeMessages.create called more times than expected")
        return _Message(self._responses.pop(0))


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.messages = FakeMessages(responses)
