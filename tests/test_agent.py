from langchain_core.messages import AIMessage, HumanMessage

from research_agent.agent import fix_fallback_block_fields

FALLBACK = {
    "type": "fallback",
    "from_": {"model": "claude-opus-5-5"},
    "to": {"model": "claude-opus-4-8"},
    "trigger": {"type": "refusal"},
}


def test_restores_from_key_in_fallback_block():
    text = {"type": "text", "text": "Answer"}
    message = AIMessage([FALLBACK, text], id="m1")
    fixed = fix_fallback_block_fields(message)
    assert fixed.content[0] == {
        "type": "fallback",
        "from": {"model": "claude-opus-5-5"},
        "to": {"model": "claude-opus-4-8"},
        "trigger": {"type": "refusal"},
    }
    assert fixed.content[1] == text
    assert fixed.id == "m1"
    assert "from_" in message.content[0], "original message must not be mutated"


def test_leaves_other_messages_untouched():
    plain = AIMessage("just text")
    human = HumanMessage("question")
    assert fix_fallback_block_fields(plain) is plain
    assert fix_fallback_block_fields(human) is human
