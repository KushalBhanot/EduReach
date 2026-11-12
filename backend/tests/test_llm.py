import asyncio

import pytest

from app import llm
from tests.fakes import FakeClient, api_error, response


def run(client, tier="fast", **kw):
    return asyncio.run(llm.generate(client, tier, [], system="sys", **kw))


def test_primary_model_answers():
    client = FakeClient({"gemini-3.1-flash-lite": [response("hi", prompt=1000, output=100, thoughts=50)]})
    result = run(client)
    assert result.text == "hi"
    assert result.model == "gemini-3.1-flash-lite"
    assert not result.used_fallback
    assert result.output_tokens == 150  # thoughts are billed as output
    assert result.cost_usd == pytest.approx((1000 * 0.25 + 150 * 1.50) / 1e6)


@pytest.mark.parametrize("code", [404, 429, 500, 503])
def test_falls_back_on_retryable_errors(code):
    client = FakeClient({
        "gemma-4-26b-a4b-it-maas": [api_error(code)],
        "gemini-3.1-flash-lite": [response("fallback answer")],
    })
    result = run(client, tier="smart")
    assert result.model == "gemini-3.1-flash-lite"
    assert result.used_fallback
    assert result.failed_attempts[0].code == code


def test_bad_request_does_not_fall_back():
    client = FakeClient({"gemini-3.1-flash-lite": [api_error(400)]})
    with pytest.raises(llm.UpstreamError):
        run(client)
    assert len(client.calls) == 1


def test_all_429_is_quota_exhausted():
    client = FakeClient({
        "gemini-3.1-flash-lite": [api_error(429)],
        "gemini-3.5-flash-lite": [api_error(429)],
    })
    with pytest.raises(llm.QuotaExhaustedError):
        run(client)


def test_mixed_failures_are_upstream_error():
    client = FakeClient({
        "gemini-3.1-flash-lite": [api_error(429)],
        "gemini-3.5-flash-lite": [api_error(503)],
    })
    with pytest.raises(llm.UpstreamError):
        run(client)


def test_thought_parts_are_separated():
    client = FakeClient({"gemini-3.1-flash-lite": [response("answer", thought="reasoning")]})
    result = run(client, deep_thinking=True)
    assert (result.text, result.thinking) == ("answer", "reasoning")


def test_gemma_inline_thinking_is_parsed():
    raw = "<|channel>thought step one<channel|>The answer is 4."
    client = FakeClient({"gemma-4-26b-a4b-it-maas": [response(raw)]})
    result = run(client, tier="smart")
    assert result.text == "The answer is 4."
    assert result.thinking == "step one"


def test_gemma_gets_no_thinking_config_and_low_temperature():
    client = FakeClient({"gemma-4-26b-a4b-it-maas": [response("ok")]})
    run(client, tier="smart")
    config = client.calls[0]["config"]
    assert config.thinking_config is None
    assert config.temperature == 0.4


def test_gemini_keeps_default_temperature():
    client = FakeClient({"gemini-3.1-flash-lite": [response("ok")]})
    run(client)
    config = client.calls[0]["config"]
    assert config.temperature is None
    assert config.thinking_config.include_thoughts is False
