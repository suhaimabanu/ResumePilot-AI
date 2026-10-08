"""AI provider abstraction. The rest of the app depends only on this interface."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod


class AIError(Exception):
    """Provider failure (network, quota, timeout)."""


class AIResponseError(AIError):
    """Provider answered, but the answer was malformed or incomplete."""


class AIProvider(ABC):
    name: str = "base"

    @property
    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate_json(self, system: str, prompt: str, *, task: str, temperature: float = 0.2) -> dict:
        """Return a parsed JSON object. Raise AIResponseError on malformed/truncated output."""


def parse_json_text(text: str) -> dict:
    """Parse JSON from a model response, tolerating code fences."""
    if not text or not text.strip():
        raise AIResponseError("empty response")
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.S)
    if fence:
        cleaned = fence.group(1)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AIResponseError("no JSON object in response")
        try:
            data = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as exc:
            raise AIResponseError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise AIResponseError("JSON root is not an object")
    return data
