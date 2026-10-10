"""Tests for the PubMed tools, using fake NCBI responses (no network, no API keys)."""

import pytest
import requests

from research_agent.tools import pubmed


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(pubmed.time, "sleep", lambda seconds: None)


def fake_ncbi(monkeypatch, responses):
    """Make requests.get return the given responses in order, and record each call."""
    calls = []

    def fake_get(url, params, timeout):
        calls.append(url.rsplit("/", 1)[-1])
        return responses.pop(0)

    monkeypatch.setattr(pubmed.requests, "get", fake_get)
    return calls


SEARCH_HIT = FakeResponse(json_data={"esearchresult": {"idlist": ["111", "222"]}})
SUMMARIES = FakeResponse(
    json_data={
        "result": {
            "111": {"title": "Paper one", "source": "Nature", "pubdate": "2025 Jan"},
            "222": {"title": "Paper two", "source": "Science", "pubdate": "2026 Mar 3"},
        }
    }
)


def test_search_formats_each_paper(monkeypatch):
    fake_ncbi(monkeypatch, [SEARCH_HIT, SUMMARIES])
    result = pubmed.search_pubmed.invoke({"query": "protein design"})
    assert result.splitlines() == [
        "PMID 111: Paper one (Nature, 2025)",
        "PMID 222: Paper two (Science, 2026)",
    ]


def test_search_with_no_hits(monkeypatch):
    calls = fake_ncbi(monkeypatch, [FakeResponse(json_data={"esearchresult": {"idlist": []}})])
    assert pubmed.search_pubmed.invoke({"query": "nothing matches"}) == "No results."
    assert calls == ["esearch.fcgi"]


def test_search_retries_after_rate_limit(monkeypatch):
    calls = fake_ncbi(monkeypatch, [FakeResponse(429), SEARCH_HIT, SUMMARIES])
    result = pubmed.search_pubmed.invoke({"query": "protein design"})
    assert "PMID 111" in result
    assert calls == ["esearch.fcgi", "esearch.fcgi", "esummary.fcgi"]


def test_search_error_is_returned_to_the_model(monkeypatch):
    fake_ncbi(monkeypatch, [FakeResponse(500)])
    result = pubmed.search_pubmed.invoke({"query": "protein design"})
    assert result.startswith("PubMed search failed")


def test_get_abstract(monkeypatch):
    fake_ncbi(monkeypatch, [FakeResponse(text="An abstract.")])
    assert pubmed.get_abstract.invoke({"pmid": "111"}) == "An abstract."


def test_get_abstract_error_is_returned_to_the_model(monkeypatch):
    fake_ncbi(monkeypatch, [FakeResponse(429), FakeResponse(429), FakeResponse(429)])
    assert pubmed.get_abstract.invoke({"pmid": "111"}).startswith("Could not fetch PMID 111")
