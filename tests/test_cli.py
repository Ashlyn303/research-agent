import logging
import subprocess
import sys

from langchain_core.messages import AIMessage

from research_agent import cli


class FakeAgent:
    def __init__(self, reply: AIMessage):
        self.reply = reply
        self.questions: list[str] = []
        self.configs: list[dict | None] = []

    def invoke(self, state, config=None):
        self.questions.append(state["messages"][0]["content"])
        self.configs.append(config)
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


def test_trace_metadata_is_attached(monkeypatch):
    _, agent = run_cli(monkeypatch, AIMessage("answer"), ["question"])
    metadata = agent.configs[0]["metadata"]
    assert metadata["model"] == "claude-sonnet-5-5"
    assert {"prompt_version", "git_commit", "app_version"} <= set(metadata)
    assert "cli" in agent.configs[0]["tags"]


def test_verbose_logs_usage_summary(monkeypatch, caplog):
    reply = AIMessage(
        "answer",
        usage_metadata={"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100},
        response_metadata={"model_name": "claude-sonnet-5-5"},
    )
    with caplog.at_level(logging.INFO):
        run_cli(monkeypatch, reply, ["-v", "question"])
    assert "1,100 tokens, cost $0.003" in caplog.text
