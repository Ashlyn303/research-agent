"""Automatic checks on agent runs. Pure functions, unit-tested, no API calls."""

import re

from langchain_core.messages import BaseMessage, ToolMessage

# PMIDs are 1-9 digit numbers; requiring 6+ digits avoids years and most quantities.
PMID_RE = re.compile(r"(?<![\w.])\d{6,9}(?![\w.])")
ARXIV_RE = re.compile(r"(?<![\w.])\d{4}\.\d{4,5}(?![\w])")


def extract_ids(text: str) -> set[str]:
    """Find PMIDs and arXiv IDs mentioned in text."""
    return set(PMID_RE.findall(text)) | set(ARXIV_RE.findall(text))


def retrieved_ids(messages: list[BaseMessage]) -> list[str]:
    """IDs of all sources that appeared in tool results during a run."""
    found: set[str] = set()
    for message in messages:
        if isinstance(message, ToolMessage):
            found |= extract_ids(str(message.content))
    return sorted(found)


def citation_validity(cited: set[str], retrieved: set[str]) -> float:
    """Fraction of cited IDs that the agent actually retrieved (1.0 if nothing is cited)."""
    if not cited:
        return 1.0
    return len(cited & retrieved) / len(cited)


def must_retrieve_recall(must: list[str], retrieved: set[str]) -> float | None:
    """Fraction of required sources that were retrieved (None if the case requires none)."""
    if not must:
        return None
    return len(set(must) & retrieved) / len(must)
