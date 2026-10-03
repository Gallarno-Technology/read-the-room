"""Tests for SentimentService + the SentimentProvider seam.

The service is exercised with a fake provider (no network) to prove:
  - the provider seam is honoured (service passes rubric + user message + schema,
    stamps the provider's model_id and the rubric_version onto the result),
  - no-lyrics never calls the provider (spike lock),
  - provider failure / empty result degrades to None (route-to-review),
  - confidence="unknown" is surfaced (not swallowed) for the caller to fail-safe.

AnthropicProvider is exercised with a fake anthropic client to prove the
tool-use block is parsed and forced correctly, without hitting the API.

asyncio_mode = "auto" — no @pytest.mark.asyncio needed.
"""
import time

import pytest

from sentiment_provider import AnthropicProvider, SentimentProvider
from sentiment_service import OUTPUT_SCHEMA, SentimentService, SongAnalysis


# ---------------------------------------------------------------------------
# A fake provider — the whole point of the seam: no SDK, no network.
# ---------------------------------------------------------------------------
class FakeProvider(SentimentProvider):
    def __init__(self, result, model_id="fake-model-1"):
        self._result = result
        self._model_id = model_id
        self.calls = []

    @property
    def model_id(self):
        return self._model_id

    def evaluate(self, system_prompt, user_message, schema):
        self.calls.append((system_prompt, user_message, schema))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _rating(confidence="known", **cat_over):
    cats = {
        "sexual": {"severity": "none", "reason": ""},
        "drug_references": {"severity": "none", "reason": ""},
        "violence": {"severity": "graphic", "reason": "first-person shooter POV"},
        "dark_themes": {"severity": "none", "reason": ""},
        "language": {"severity": "none", "reason": ""},
    }
    cats.update(cat_over)
    return {
        "categories": cats,
        "framing": "neutral",
        "confidence": confidence,
        "verdict": {"family_friendly": "decline", "mixed_company": "decline", "close_friends": "pass"},
        "summary": "Graphic violence; declines FF/MC, passes CF.",
    }


@pytest.fixture
def rubric(tmp_path):
    p = tmp_path / "rubric.md"
    p.write_text("RUBRIC TEXT")
    return p


# ---------------------------------------------------------------------------
# Seam behaviour
# ---------------------------------------------------------------------------

async def test_evaluate_delegates_to_provider_and_stamps(rubric):
    provider = FakeProvider(_rating(), model_id="fake-model-1")
    svc = SentimentService(provider=provider, rubric_version="v2", rubric_path=rubric)

    analysis = await svc.evaluate("t1", "Pumped Up Kicks", "Foster the People", "all the other kids...")

    assert isinstance(analysis, SongAnalysis)
    assert analysis.violence.severity == "graphic"
    assert analysis.confidence == "known"
    # service stamps identity from the provider + its own rubric_version
    assert analysis.model_id == "fake-model-1"
    assert analysis.rubric_version == "v2"
    assert analysis.evaluated_at > 0.0

    # provider received the rubric text, a user message with the lyrics, and the schema
    sys_prompt, user_msg, schema = provider.calls[0]
    assert sys_prompt == "RUBRIC TEXT"
    assert "Pumped Up Kicks" in user_msg and "all the other kids" in user_msg
    assert schema is OUTPUT_SCHEMA


async def test_no_lyrics_never_calls_provider(rubric):
    provider = FakeProvider(_rating())
    svc = SentimentService(provider=provider, rubric_path=rubric)

    assert await svc.evaluate("t1", "Song", "Artist", None) is None
    assert await svc.evaluate("t1", "Song", "Artist", "   ") is None
    assert provider.calls == []  # spike lock: no LLM without lyrics


async def test_provider_failure_returns_none(rubric):
    provider = FakeProvider(RuntimeError("api down"))
    svc = SentimentService(provider=provider, rubric_path=rubric)
    assert await svc.evaluate("t1", "Song", "Artist", "lyrics") is None


async def test_provider_empty_result_returns_none(rubric):
    provider = FakeProvider(None)
    svc = SentimentService(provider=provider, rubric_path=rubric)
    assert await svc.evaluate("t1", "Song", "Artist", "lyrics") is None


async def test_confidence_unknown_is_surfaced(rubric):
    """Service returns the analysis with confidence=unknown intact — it does NOT
    swallow it; the caller (content_checker) is responsible for the fail-safe."""
    provider = FakeProvider(_rating(confidence="unknown"))
    svc = SentimentService(provider=provider, rubric_path=rubric)
    analysis = await svc.evaluate("t1", "Song", "Artist", "lyrics")
    assert analysis is not None
    assert analysis.confidence == "unknown"


class SlowProvider(SentimentProvider):
    """Simulates a stalled network call (not an exception) — exactly the kind
    of hang that used to leave 'Checking…' frozen forever."""

    def __init__(self, delay):
        self._delay = delay

    @property
    def model_id(self):
        return "slow-model"

    def evaluate(self, system_prompt, user_message, schema):
        time.sleep(self._delay)
        return _rating()


async def test_evaluate_times_out_and_degrades_to_none(rubric):
    svc = SentimentService(
        provider=SlowProvider(delay=0.3), rubric_path=rubric, timeout_seconds=0.05
    )
    start = time.monotonic()
    result = await svc.evaluate("t1", "Song", "Artist", "lyrics")
    elapsed = time.monotonic() - start

    assert result is None
    assert elapsed < 0.2, f"evaluate() should be bounded by timeout_seconds, took {elapsed:.3f}s"


def test_default_provider_is_anthropic():
    """With no provider injected, the service builds an AnthropicProvider."""
    svc = SentimentService(api_key="sk-test", model="claude-haiku-4-5-20251001")
    assert isinstance(svc.provider, AnthropicProvider)
    assert svc.provider.model_id == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# AnthropicProvider — parse the tool_use block via a fake client (no network)
# ---------------------------------------------------------------------------

class _Block:
    def __init__(self, type_, input_=None):
        self.type = type_
        self.input = input_


class _Resp:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, resp):
        self._resp = resp
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._resp


class _FakeAnthropic:
    def __init__(self, resp):
        self.messages = _FakeMessages(resp)


def test_anthropic_provider_extracts_tool_use_input():
    rating = _rating()
    resp = _Resp([_Block("text", None), _Block("tool_use", rating)])
    fake = _FakeAnthropic(resp)

    provider = AnthropicProvider(api_key="sk-test", model="claude-haiku-4-5-20251001")
    provider._client = fake  # inject fake client, bypass lazy SDK import

    out = provider.evaluate("SYS", "USER", OUTPUT_SCHEMA)
    assert out == rating

    kw = fake.messages.last_kwargs
    assert kw["model"] == "claude-haiku-4-5-20251001"
    assert kw["tool_choice"] == {"type": "tool", "name": "rate_song"}
    assert kw["tools"][0]["input_schema"] is OUTPUT_SCHEMA
    # rubric sent as a cached system block
    assert kw["system"][0]["text"] == "SYS"
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_anthropic_provider_returns_none_without_tool_use():
    resp = _Resp([_Block("text", None)])  # model refused to call the tool
    provider = AnthropicProvider(api_key="sk-test")
    provider._client = _FakeAnthropic(resp)
    assert provider.evaluate("SYS", "USER", OUTPUT_SCHEMA) is None


def test_anthropic_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(api_key=None)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        provider._get_client()
