"""Google Gemini provider (google-genai SDK). The API key stays on the server."""
from __future__ import annotations

import logging
import threading
import time

from ..core.config import settings
from .base import AIError, AIProvider, AIResponseError, parse_json_text

log = logging.getLogger("ai.gemini")

# HTTP codes meaning "this model can't serve us right now" (retired, quota, overloaded, timed out):
# the provider moves on to the next configured model instead of failing the whole request.
_UNAVAILABLE_CODES = {404, 429, 500, 503, 504}
_COOLDOWN_S = 60  # short: a single 503 blip must not push the main tailoring call onto a weaker model
_cooldown: dict[str, float] = {}  # model -> time until which it is skipped
# Tasks whose output quality is the product: strong models only, more patient retries.
QUALITY_TASKS = {"tailor", "repair"}


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 fallback_models: list[str] | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model
        fallbacks = settings.gemini_fallback_models if fallback_models is None else fallback_models
        self.models = list(dict.fromkeys([self.model, *fallbacks]))
        self.last_model: str | None = None
        self._client = None
        self._client_lock = threading.Lock()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _candidate_models(self, task: str) -> list[str]:
        models = self.models
        if task in QUALITY_TASKS:  # "lite" models only make cosmetic edits — never use them to rewrite a resume
            models = [m for m in models if "lite" not in m] or models
        now = time.time()
        ready = [m for m in models if _cooldown.get(m, 0) <= now]
        return ready or models  # everything cooling down → try them all anyway

    def _get_client(self):
        # Locked: parallel tasks (structure + JD) racing here would build two clients, and the discarded
        # one closes the shared HTTP transport ("Cannot send a request, as the client has been closed").
        with self._client_lock:
            return self._make_client()

    def _make_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=settings.gemini_timeout_s * 1000),
            )
        return self._client

    def generate_json(self, system: str, prompt: str, *, task: str, temperature: float = 0.2) -> dict:
        if not self.available:
            raise AIError("Gemini API key is not configured")
        from google.genai import types

        last_exc: Exception | None = None
        quality = task in QUALITY_TASKS
        attempts = settings.gemini_max_retries + (3 if quality else 1)
        for attempt in range(attempts):
            if attempt:  # overload spikes usually pass within a minute: wait longer before quality retries
                time.sleep(min(20, 3 * 2 ** (attempt - 1)) if quality else min(8, 1.5 * 2 ** (attempt - 1)))
            for model in self._candidate_models(task):
                started = time.time()
                try:
                    resp = self._get_client().models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system,
                            temperature=temperature,
                            response_mime_type="application/json",
                            max_output_tokens=32768,
                        ),
                    )
                    finish = None
                    if resp.candidates:
                        finish = str(getattr(resp.candidates[0], "finish_reason", "") or "")
                    if finish and "MAX_TOKENS" in finish:
                        raise AIResponseError("response truncated (max tokens)")
                    if finish and ("SAFETY" in finish or "RECITATION" in finish):
                        raise AIResponseError(f"response blocked ({finish})")
                    data = parse_json_text(resp.text or "")
                    log.info("gemini task=%s model=%s ok in %.1fs (attempt %d)", task, model, time.time() - started,
                             attempt + 1)
                    self.last_model = model
                    return data
                except AIResponseError as exc:
                    last_exc = exc
                    log.warning("gemini task=%s model=%s malformed response (attempt %d): %s", task, model,
                                attempt + 1, exc)
                except Exception as exc:  # network / quota / timeout
                    last_exc = exc
                    code = getattr(exc, "code", None)
                    log.warning("gemini task=%s model=%s call failed (attempt %d): %s %s", task, model, attempt + 1,
                                type(exc).__name__, code or str(exc)[:160])
                    if code in _UNAVAILABLE_CODES:  # overloaded / quota / retired → skip it for a while
                        _cooldown[model] = time.time() + _COOLDOWN_S
        if isinstance(last_exc, AIResponseError):
            raise last_exc
        raise AIError(f"Gemini request failed: {type(last_exc).__name__}") from last_exc
