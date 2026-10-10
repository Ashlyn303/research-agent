from research_agent.config import Settings
from research_agent.run_info import prompt_version, run_config


def test_prompt_version_is_stable_short_hash():
    assert prompt_version() == prompt_version()
    assert len(prompt_version()) == 8


def test_run_config_tags_model_and_source(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    config = run_config(Settings(model="claude-haiku-5-5"), "evals")
    assert config["tags"] == ["evals", "claude-haiku-5-5"]
    assert config["metadata"]["model"] == "claude-haiku-5-5"
    assert config["metadata"]["source"] == "evals"
