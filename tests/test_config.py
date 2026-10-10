import pytest

from research_agent.config import DEFAULT_MODEL, ConfigError, load_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ["ANTHROPIC_API_KEY", "MODEL", "LANGSMITH_TRACING", "LANGSMITH_API_KEY"]:
        monkeypatch.delenv(name, raising=False)


def test_missing_api_key_gives_clear_error():
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_settings()


def test_empty_api_key_is_rejected(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_settings()


def test_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    settings = load_settings()
    assert settings.model == DEFAULT_MODEL
    assert settings.langsmith_tracing is False


def test_key_is_hidden_when_printed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert "test-key" not in repr(load_settings())


def test_tracing_without_langsmith_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    with pytest.raises(ConfigError, match="LANGSMITH_API_KEY"):
        load_settings()
