"""Minimal research agent: searches PubMed and summarizes what it finds."""

import os
import sys
import threading
import time

import requests
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain.agents import create_agent

load_dotenv()

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI allows 3 requests/second without an API key. Claude often calls tools in
# parallel, so space requests out and retry when NCBI says we're going too fast.
_ncbi_lock = threading.Lock()
_last_request = 0.0


def _eutils(endpoint: str, params: dict) -> requests.Response:
    global _last_request
    for attempt in range(3):
        with _ncbi_lock:
            wait = 0.4 - (time.monotonic() - _last_request)
            if wait > 0:
                time.sleep(wait)
            _last_request = time.monotonic()
        response = requests.get(f"{EUTILS}/{endpoint}", params=params, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        time.sleep(1 + attempt)
    response.raise_for_status()


@tool
def search_pubmed(query: str, max_results: int = 5) -> str:
    """Search PubMed and return titles, journals, years and PMIDs of matching papers."""
    try:
        ids = _eutils(
            "esearch.fcgi",
            {"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"},
        ).json()["esearchresult"]["idlist"]
        if not ids:
            return "No results."
        summaries = _eutils(
            "esummary.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        ).json()["result"]
    except (requests.RequestException, KeyError) as e:
        return f"PubMed search failed ({e!r}). Try again or rephrase the query."
    return "\n".join(
        f"PMID {pmid}: {summaries[pmid]['title']} ({summaries[pmid]['source']}, {summaries[pmid]['pubdate'][:4]})"
        for pmid in ids
    )


@tool
def get_abstract(pmid: str) -> str:
    """Fetch the abstract of one PubMed paper by its PMID."""
    try:
        return _eutils(
            "efetch.fcgi", {"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text"}
        ).text
    except requests.RequestException as e:
        return f"Could not fetch PMID {pmid} ({e!r})."


# If Claude's safety classifier declines a request (e.g. a false positive on a
# biology question), the API retries it on a fallback model inside the same call.
model = init_chat_model(
    os.getenv("MODEL", "claude-opus-5-5"),
    model_provider="anthropic",
    betas=["server-side-fallback-2026-07-01"],
    model_kwargs={"extra_body": {"fallbacks": "default"}},
)

agent = create_agent(
    model,
    tools=[search_pubmed, get_abstract],
    system_prompt=(
        "You are a research assistant. Search PubMed, read the most relevant abstracts, "
        "and answer with a short summary that cites papers by PMID."
    ),
)

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What are recent approaches to de novo protein design?"
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    final = result["messages"][-1]
    if final.response_metadata.get("stop_reason") == "refusal":
        print("Claude declined this request:", final.response_metadata.get("stop_details"))
    else:
        print(final.text)
