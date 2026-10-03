#!/usr/bin/env python3
"""Read the Room — the pluggable AI-backend seam.

The content evaluator is model-agnostic. `SentimentProvider` is the extension
point: given the rubric (system prompt), a rendered user message, and the JSON
output schema, a provider returns a dict conforming to that schema — the model's
structured rating — or None on failure. Everything model-specific (which SDK,
how structured output is forced, the model id, pricing) lives behind this
interface; the rest of the pipeline (sentiment_service, cache, profiles) never
imports an SDK.

This repo ships exactly one implementation, `AnthropicProvider` (Claude), which
is what the project was benchmarked on. It is deliberately NOT the only thing
that could sit here: to run any other backend — OpenAI, a local Ollama model, a
gateway, a test double — implement `SentimentProvider.evaluate` and pass an
instance to `SentimentService(provider=...)`. No changes to the core are needed.

Contract for implementers:
  - `model_id`: a stable identifier, stored in the analysis cache so a model
    change self-invalidates stale rows (see sentiment_cache D-05).
  - `evaluate(system_prompt, user_message, schema)` is SYNCHRONOUS and may block
    on network I/O — SentimentService runs it in a thread executor. Return a
    dict matching `schema` (at least its `categories`/`framing`/`confidence`
    keys — the `verdict` block, if present, is ignored; code derives verdicts).
    Return None (or raise) to signal failure; the caller routes the track to
    manual review and does not cache it.
"""
from __future__ import annotations

import abc
import os

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


class SentimentProvider(abc.ABC):
    """Abstract AI backend for lyric content evaluation. The seam that lets any
    model plug in without touching the rest of the pipeline."""

    @property
    @abc.abstractmethod
    def model_id(self) -> str:
        """Stable identifier for the model, stamped into the analysis cache."""
        ...

    @abc.abstractmethod
    def evaluate(self, system_prompt: str, user_message: str, schema: dict) -> dict | None:
        """Return the model's structured rating as a dict conforming to `schema`,
        or None on failure. Synchronous; may block on I/O."""
        ...


class AnthropicProvider(SentimentProvider):
    """Claude backend using forced tool-use for structured output plus prompt
    caching on the rubric (the system prompt is identical across every call, so
    it is billed at the cached-read rate after the first). Mirrors the pattern
    validated in the spike's `clients.call_claude_haiku`.

    The `anthropic` SDK is imported lazily on first call so importing this module
    (and the pipeline that depends on it) never requires the SDK to be installed
    — only actually evaluating with this provider does.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        max_tokens: int = 1024,
        timeout: float = 15.0,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = None  # lazily constructed anthropic.Anthropic

    @property
    def model_id(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None:
            import anthropic  # deferred so the module imports without the SDK

            if not self._api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set — cannot evaluate")
            # Explicit timeout/max_retries — this is what actually unblocks the
            # run_in_executor thread on a stalled connection; the asyncio.wait_for
            # in SentimentService.evaluate() alone can't cancel this thread.
            self._client = anthropic.Anthropic(
                api_key=self._api_key, timeout=self._timeout, max_retries=self._max_retries
            )
        return self._client

    def evaluate(self, system_prompt: str, user_message: str, schema: dict) -> dict | None:
        client = self._get_client()
        tool_def = {
            "name": "rate_song",
            "description": "Emit the structured rating for the song.",
            "input_schema": schema,
        }
        # cache_control on the rubric → cached-read pricing after the first call.
        system_blocks = [
            {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
        ]
        resp = client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_blocks,
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "rate_song"},
            messages=[{"role": "user", "content": user_message}],
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        return block.input if block is not None else None
