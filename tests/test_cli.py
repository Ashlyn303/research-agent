import logging
import subprocess
import sys

from langchain_core.messages import AIMessage

from research_agent import cli


class FakeAgent:
    def __init__(self, reply: AIMessage):
        self.reply = reply
        self.questions = []

    def invoke(self, state):
        self.questions.append(state["messages"][0]["content"])
        return {"messages": [self.reply]}


def run_cli(monkeypatch, reply, argv):
    agent = FakeAgent(reply)
    monkeypatch.setattr(cli, "load_dotenv", lambda path: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(cli, "build_agent", lambda settings: agent)
    return cli.main(argv), agent


def test_prints_answer(monkeypatch, capsys):
    code, agent = run_cli(
        monkeypatch, AIMessage("Summary (PMID 1)"), ["what", "is", "RFdiffusion?"]
    )
    assert code == 0
    assert agent.questions == ["what is RFdiffusion?"]
    assert capsys.readouterr().out.strip() == "Summary (PMID 1)"


def test_refusal_exits_with_error(monkeypatch, caplog):
    refusal = AIMessage(
        [], response_metadata={"stop_reason": "refusal", "stop_details": {"category": "bio"}}
    )
    with caplog.at_level(logging.ERROR):
        code, _ = run_cli(monkeypatch, refusal, ["question"])
    assert code == 1
    assert "declined" in caplog.text


def test_missing_key_exits_before_building_agent(monkeypatch, caplog):
    monkeypatch.setattr(cli, "load_dotenv", lambda path: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(cli, "build_agent", lambda settings: (_ for _ in ()).throw(AssertionError))
    with caplog.at_level(logging.ERROR):
        assert cli.main(["question"]) == 2
    assert "ANTHROPIC_API_KEY" in caplog.text


def test_importing_package_has_no_side_effects():
    """Importing must not need API keys or build a model."""
    code = "import research_agent.cli, research_agent.agent, research_agent.tools"
    env = {"PATH": "", "LANGSMITH_TRACING": "false"}
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
