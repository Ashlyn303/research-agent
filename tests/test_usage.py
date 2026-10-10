import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from research_agent.usage import message_cost, summarize_usage


def call(model, input_tokens, output_tokens, cache_read=0, cache_creation=0, tool_calls=()):
    return AIMessage(
        "",
        tool_calls=[{"name": "t", "args": {}, "id": str(i)} for i in range(len(tool_calls))],
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_token_details": {"cache_read": cache_read, "cache_creation": cache_creation},
        },
        response_metadata={"model_name": model},
    )


def test_cost_uses_the_model_that_served_the_call():
    # 1M input + 1M output tokens
    assert message_cost(call("claude-sonnet-5-5", 1_000_000, 1_000_000)) == pytest.approx(12.0)
    assert message_cost(call("claude-opus-5-5", 1_000_000, 1_000_000)) == pytest.approx(24.0)


def test_cache_reads_and_writes_are_priced_separately():
    # Sonnet input $2/M: 200k uncached, 600k cache reads at 10%, 200k cache writes at 125%
    message = call("claude-sonnet-5-5", 1_000_000, 0, cache_read=600_000, cache_creation=200_000)
    assert message_cost(message) == pytest.approx(0.4 + 0.12 + 0.5)


def test_unknown_model_is_not_priced():
    assert message_cost(call("some-other-model", 1000, 100)) is None


def test_summarize_usage_over_a_run():
    messages = [
        HumanMessage("q"),
        call("claude-sonnet-5-5", 10_000, 500, tool_calls=["a", "b"]),
        ToolMessage("result", tool_call_id="0"),
        call("claude-opus-4-8", 20_000, 1_000),
        call("mystery-model", 100, 10),
    ]
    usage = summarize_usage(messages, seconds=12.3)
    assert usage.model_calls == 3
    assert usage.tool_calls == 2
    assert usage.total_tokens == 31_610
    assert usage.cost_usd == pytest.approx(0.025 + 0.125)
    assert usage.unpriced_models == {"mystery-model"}
    assert "excludes mystery-model" in usage.summary()
