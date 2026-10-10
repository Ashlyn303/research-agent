"""Token, cost and timing summary for one agent run."""

from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage

# USD per million tokens (input, output) from Anthropic's price list. Update when prices change.
# Cache reads cost 10% and cache writes 125% of the input price.
PRICES_PER_MTOK = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-opus-4-8": (5.00, 25.00),
}


@dataclass
class RunUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_calls: int = 0
    tool_calls: int = 0
    seconds: float = 0.0
    unpriced_models: frozenset[str] = frozenset()

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def summary(self) -> str:
        cost = f"${self.cost_usd:.3f}"
        if self.unpriced_models:
            cost += f" (excludes {', '.join(sorted(self.unpriced_models))})"
        return (
            f"{self.total_tokens:,} tokens, cost {cost}, {self.seconds:.0f}s, "
            f"{self.model_calls} model calls, {self.tool_calls} tool calls"
        )


def message_cost(message: AIMessage) -> float | None:
    """Cost of one model call, priced by the model that served it (None if unknown)."""
    usage = message.usage_metadata
    model = message.response_metadata.get("model_name", "")
    prices = next((p for name, p in PRICES_PER_MTOK.items() if model.startswith(name)), None)
    if not usage or prices is None:
        return None
    input_price, output_price = prices
    details = usage.get("input_token_details") or {}
    cache_read = details.get("cache_read", 0) or 0
    cache_write = details.get("cache_creation", 0) or 0
    uncached = max(usage["input_tokens"] - cache_read - cache_write, 0)
    dollars = (
        uncached * input_price
        + cache_read * input_price * 0.10
        + cache_write * input_price * 1.25
        + usage["output_tokens"] * output_price
    )
    return dollars / 1_000_000


def summarize_usage(messages: list[BaseMessage], seconds: float = 0.0) -> RunUsage:
    usage = RunUsage(seconds=seconds)
    unpriced = set()
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        usage.tool_calls += len(message.tool_calls)
        if message.usage_metadata:
            usage.model_calls += 1
            usage.input_tokens += message.usage_metadata["input_tokens"]
            usage.output_tokens += message.usage_metadata["output_tokens"]
            cost = message_cost(message)
            if cost is None:
                unpriced.add(message.response_metadata.get("model_name", "unknown"))
            else:
                usage.cost_usd += cost
    usage.unpriced_models = frozenset(unpriced)
    return usage
