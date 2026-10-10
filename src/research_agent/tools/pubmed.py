"""PubMed tools backed by NCBI E-utilities."""

import logging
import threading
import time

import requests
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI allows 3 requests/second without an API key. Claude often calls tools in
# parallel, so space requests out and retry when NCBI says we're going too fast.
MIN_INTERVAL_SECONDS = 0.4
MAX_ATTEMPTS = 3

_ncbi_lock = threading.Lock()
_last_request = 0.0


def _eutils(endpoint: str, params: dict) -> requests.Response:
    global _last_request
    for attempt in range(1, MAX_ATTEMPTS + 1):
        with _ncbi_lock:
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
            if wait > 0:
                time.sleep(wait)
            _last_request = time.monotonic()
        response = requests.get(f"{EUTILS}/{endpoint}", params=params, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        logger.warning("NCBI rate limit on %s (attempt %d/%d)", endpoint, attempt, MAX_ATTEMPTS)
        time.sleep(attempt)
    response.raise_for_status()
    raise AssertionError("unreachable: 429 responses raise in raise_for_status")


@tool
def search_pubmed(query: str, max_results: int = 5, min_year: int | None = None) -> str:
    """Search PubMed and return titles, journals, years and PMIDs of matching papers.

    Results are ordered by relevance. Set min_year to only include papers published in or
    after that year, e.g. for questions about recent work.
    """
    logger.info(
        "Searching PubMed: %r (max %d, from %s)", query, max_results, min_year or "any year"
    )
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        # PubMed's default order is newest first, which surfaces off-topic papers.
        "sort": "relevance",
    }
    if min_year is not None:
        params |= {"datetype": "pdat", "mindate": str(min_year), "maxdate": "3000"}
    try:
        ids = _eutils("esearch.fcgi", params).json()["esearchresult"]["idlist"]
        if not ids:
            return "No results."
        summaries = _eutils(
            "esummary.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        ).json()["result"]
    except (requests.RequestException, KeyError) as e:
        logger.error("PubMed search failed for %r: %r", query, e)
        return f"PubMed search failed ({e!r}). Try again or rephrase the query."
    lines = []
    for pmid in ids:
        paper = summaries[pmid]
        lines.append(f"PMID {pmid}: {paper['title']} ({paper['source']}, {paper['pubdate'][:4]})")
    return "\n".join(lines)


@tool
def get_abstract(pmid: str) -> str:
    """Fetch the abstract of one PubMed paper by its PMID."""
    logger.info("Fetching abstract for PMID %s", pmid)
    try:
        return _eutils(
            "efetch.fcgi", {"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text"}
        ).text
    except requests.RequestException as e:
        logger.error("Could not fetch PMID %s: %r", pmid, e)
        return f"Could not fetch PMID {pmid} ({e!r})."
