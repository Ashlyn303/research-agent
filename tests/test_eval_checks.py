from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from evals.checks import citation_validity, extract_ids, must_retrieve_recall, summarize_run
from evals.run import load_cases


def test_extract_ids_finds_pmids_and_arxiv_ids():
    text = "RFdiffusion (PMID 37433327; PMIDs 36108050, 41562285) and ReAct (arXiv 2210.03629)."
    assert extract_ids(text) == {"37433327", "36108050", "41562285", "2210.03629"}


def test_extract_ids_ignores_years_quantities_and_embedded_numbers():
    text = "In 2023, kcat/Km reached 53,000 M-1s-1 (10.1038/s41586-023-06415-8, PMC1234567)."
    assert extract_ids(text) == set()


def test_summarize_run_collects_retrieved_ids_tool_calls_and_tokens():
    messages = [
        HumanMessage("question"),
        AIMessage(
            "",
            tool_calls=[{"name": "search_pubmed", "args": {"query": "x"}, "id": "1"}],
            usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        ),
        ToolMessage("PMID 37433327: RFdiffusion (Nature, 2023)", tool_call_id="1"),
        AIMessage(
            "Answer (PMID 37433327)",
            usage_metadata={"input_tokens": 200, "output_tokens": 50, "total_tokens": 250},
        ),
    ]
    assert summarize_run(messages) == {
        "retrieved_ids": ["37433327"],
        "tool_calls": 1,
        "tokens": 370,
    }


def test_citation_validity():
    assert citation_validity({"1111111", "2222222"}, {"1111111"}) == 0.5
    assert citation_validity(set(), {"1111111"}) == 1.0


def test_must_retrieve_recall():
    assert must_retrieve_recall(["1111111", "2222222"], {"2222222", "3333333"}) == 0.5
    assert must_retrieve_recall([], {"1111111"}) is None


def test_cases_file_is_valid():
    cases = load_cases()
    assert len(cases) >= 5
    for case in cases:
        assert {"id", "category", "topic", "question", "must_retrieve", "key_points"} <= set(case)
        assert case["category"] in {"research", "learning", "no-evidence"}
        assert case["key_points"]
