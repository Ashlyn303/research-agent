"""Application settings, read from environment variables (and `.env` via the CLI)."""

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sonnet for development and evals; set MODEL=claude-opus-5-5 for final checks.
DEFAULT_MODEL = "claude-sonnet-5-5"


class ConfigError(Exception):
    """Raised when required settings are missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: SecretStr = Field(min_length=1)
    model: str = DEFAULT_MODEL
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None


def load_settings() -> Settings:
    """Read settings from the environment, turning validation errors into a readable message."""
    try:
        settings = Settings()
    except ValidationError as e:
        problems = ", ".join(str(err["loc"][0]).upper() for err in e.errors())
        raise ConfigError(
            f"Missing or invalid setting(s): {problems}. "
            "Copy .env.example to .env and fill in your keys."
        ) from None
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        raise ConfigError("LANGSMITH_TRACING is true but LANGSMITH_API_KEY is not set.")
    return settings
