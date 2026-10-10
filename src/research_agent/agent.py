"""Builds the research agent. Nothing is created until `build_agent` is called."""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, AnyMessage

from research_agent.config import Settings
from research_agent.tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "You are a research assistant. Search PubMed, read the most relevant abstracts, "
    "and answer with a short summary that cites papers by PMID."
)


class RefusalError(Exception):
    """Raised when Claude declines the request even after the fallback model."""


def fix_fallback_block_fields(message: AnyMessage) -> AnyMessage:
    """Restore the `from` key that langchain-anthropic saves as `from_` in fallback blocks.

    When the server-side fallback runs, the response contains a `fallback` content block.
    langchain-anthropic stores it with `model_dump()` (no `by_alias`), so `from` becomes
    `from_` and the API rejects the block when the conversation is sent back
    ("fallback.from: Field required").
    """
    if not isinstance(message, AIMessage) or not isinstance(message.content, list):
        return message
    if not any(_is_broken_fallback(block) for block in message.content):
        return message
    content = [
        {("from" if key == "from_" else key): value for key, value in block.items()}
        if _is_broken_fallback(block)
        else block
        for block in message.content
    ]
    return message.model_copy(update={"content": content})


def _is_broken_fallback(block) -> bool:
    return isinstance(block, dict) and block.get("type") == "fallback" and "from_" in block


@wrap_model_call
def fix_fallback_blocks(request: ModelRequest, handler):
    messages = [fix_fallback_block_fields(m) for m in request.messages]
    return handler(request.override(messages=messages))


def build_agent(settings: Settings):
    # If Claude's safety classifier declines a request (e.g. a false positive on a
    # biology question), the API retries it on a fallback model inside the same call.
    model = init_chat_model(
        settings.model,
        model_provider="anthropic",
        api_key=settings.anthropic_api_key.get_secret_value(),
        betas=["server-side-fallback-2026-07-01"],
        model_kwargs={"extra_body": {"fallbacks": "default"}},
    )
    return create_agent(
        model, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT, middleware=[fix_fallback_blocks]
    )


def final_answer(result: dict) -> str:
    """Return the agent's final text, or raise RefusalError if Claude declined."""
    final: AIMessage = result["messages"][-1]
    if final.response_metadata.get("stop_reason") == "refusal":
        details = final.response_metadata.get("stop_details")
        raise RefusalError(f"Claude declined this request: {details}")
    return final.text
