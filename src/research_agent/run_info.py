"""Metadata attached to every LangSmith trace, so a trace can be tied to the exact code."""

import hashlib
import subprocess
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from research_agent.agent import SYSTEM_PROMPT
from research_agent.config import Settings


def prompt_version() -> str:
    """Short hash of the system prompt; changes whenever the prompt text changes."""
    return hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:8]


@cache
def git_commit() -> str:
    """Current commit of the source checkout, with -dirty for uncommitted changes."""
    repo = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit + ("-dirty" if status.strip() else "")


def package_version() -> str:
    try:
        return version("research-agent")
    except PackageNotFoundError:
        return "unknown"


def run_config(settings: Settings, source: str) -> dict:
    """LangChain run config: tags and metadata shown on the LangSmith trace."""
    return {
        "run_name": "research-agent",
        "tags": [source, settings.model],
        "metadata": {
            "model": settings.model,
            "prompt_version": prompt_version(),
            "git_commit": git_commit(),
            "app_version": package_version(),
            "source": source,
        },
    }
