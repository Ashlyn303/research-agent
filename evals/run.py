"""Run the evaluation set against the agent and record a LangSmith experiment.

Usage:
    uv run python -m evals.run                       # all cases, model from MODEL / .env
    uv run python -m evals.run --model claude-sonnet-5-5
    uv run python -m evals.run --cases react-agents,nonexistent-method
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import find_dotenv, load_dotenv
from langchain.chat_models import init_chat_model
from langsmith import Client
from pydantic import BaseModel, Field

from evals.checks import citation_validity, extract_ids, must_retrieve_recall, summarize_run
from research_agent.agent import RefusalError, build_agent, final_answer
from research_agent.config import load_settings

CASES_FILE = Path(__file__).with_name("cases.yaml")
DATASET_NAME = "research-agent-evals"
JUDGE_MODEL = "claude-haiku-5-5"


def load_cases(only: set[str] | None = None) -> list[dict]:
    cases = yaml.safe_load(CASES_FILE.read_text())
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case ids in cases.yaml")
    if only:
        unknown = only - set(ids)
        if unknown:
            raise ValueError(f"Unknown case ids: {sorted(unknown)}")
        cases = [case for case in cases if case["id"] in only]
    return cases


def sync_dataset(client: Client, cases: list[dict]) -> None:
    """Make the LangSmith dataset match cases.yaml (create, update, delete examples)."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
    else:
        dataset = client.create_dataset(
            DATASET_NAME, description="Evaluation questions from evals/cases.yaml"
        )
    existing = {
        (example.metadata or {}).get("case_id"): example
        for example in client.list_examples(dataset_id=dataset.id)
    }
    for case in cases:
        inputs = {"question": case["question"]}
        outputs = {
            "must_retrieve": case["must_retrieve"],
            "key_points": case["key_points"],
            "category": case["category"],
        }
        metadata = {"case_id": case["id"], "category": case["category"], "topic": case["topic"]}
        if case["id"] in existing:
            client.update_example(
                existing.pop(case["id"]).id, inputs=inputs, outputs=outputs, metadata=metadata
            )
        else:
            client.create_example(
                inputs=inputs, outputs=outputs, metadata=metadata, dataset_id=dataset.id
            )
    for stale in existing.values():
        client.delete_example(stale.id)


def make_target(settings):
    agent = build_agent(settings)

    def target(inputs: dict) -> dict:
        result = agent.invoke({"messages": [{"role": "user", "content": inputs["question"]}]})
        try:
            answer, refused = final_answer(result), False
        except RefusalError as e:
            answer, refused = str(e), True
        return {"answer": answer, "refused": refused, **summarize_run(result["messages"])}

    return target


# --- Evaluators: each returns {"key": ..., "score": ...}; None scores are skipped ---


def citations_valid(outputs: dict) -> dict:
    cited = extract_ids(outputs["answer"])
    return {
        "key": "citations_valid",
        "score": citation_validity(cited, set(outputs["retrieved_ids"])),
        "comment": f"cited={sorted(cited)}",
    }


def found_required_sources(outputs: dict, reference_outputs: dict) -> dict:
    must = reference_outputs["must_retrieve"]
    return {
        "key": "found_required_sources",
        "score": must_retrieve_recall(must, set(outputs["retrieved_ids"])),
        "comment": f"missing={sorted(set(must) - set(outputs['retrieved_ids']))}",
    }


def answered(outputs: dict) -> dict:
    return {"key": "answered", "score": 0.0 if outputs["refused"] else 1.0}


def tool_calls(outputs: dict) -> dict:
    return {"key": "tool_calls", "score": outputs["tool_calls"]}


def tokens(outputs: dict) -> dict:
    return {"key": "tokens", "score": outputs["tokens"]}


class KeyPointVerdict(BaseModel):
    point: str
    covered: bool
    reason: str = Field(description="one short sentence")


class JudgeResult(BaseModel):
    verdicts: list[KeyPointVerdict]


JUDGE_PROMPT = """You are grading an AI research assistant's answer against key points.

Question:
{question}

Answer:
{answer}

For each key point, decide whether the answer conveys that idea. Count it as covered if the \
idea is clearly stated anywhere in the answer, even in different words or as part of a larger \
explanation. Do not count it if the idea is missing, only hinted at, or stated incorrectly.

Key points:
{key_points}"""


def make_key_points_judge():
    judge = init_chat_model(JUDGE_MODEL, model_provider="anthropic").with_structured_output(
        JudgeResult, method="json_schema"
    )

    def key_points_covered(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
        points = reference_outputs["key_points"]
        result: JudgeResult = judge.invoke(
            JUDGE_PROMPT.format(
                question=inputs["question"],
                answer=outputs["answer"],
                key_points="\n".join(f"- {p}" for p in points),
            )
        )
        covered = sum(v.covered for v in result.verdicts)
        missed = [v.point for v in result.verdicts if not v.covered]
        return {
            "key": "key_points_covered",
            "score": covered / len(points),
            "comment": "missed: " + "; ".join(missed) if missed else "all covered",
        }

    return key_points_covered


def git_commit() -> str:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        return commit + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def print_summary(results, scored_keys: list[str]) -> None:
    rows = []
    for row in results:
        scores = {r.key: r.score for r in row["evaluation_results"]["results"]}
        rows.append((row["example"].metadata["case_id"], scores))
    width = max(len(case_id) for case_id, _ in rows)
    print("\n" + "case".ljust(width) + "  " + "  ".join(scored_keys))
    for case_id, scores in rows:
        cells = []
        for key in scored_keys:
            value = scores.get(key)
            cells.append(("-" if value is None else f"{value:g}").ljust(len(key)))
        print(case_id.ljust(width) + "  " + "  ".join(cells))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", help="model to evaluate (overrides MODEL)")
    parser.add_argument("--cases", help="comma-separated case ids to run (default: all)")
    args = parser.parse_args(argv)

    load_dotenv(find_dotenv(usecwd=True))
    settings = load_settings()
    if args.model:
        settings = settings.model_copy(update={"model": args.model})
    only = set(args.cases.split(",")) if args.cases else None

    client = Client()
    sync_dataset(client, load_cases())
    data = DATASET_NAME
    if only:
        load_cases(only)  # validates the ids
        data = [
            example
            for example in client.list_examples(dataset_name=DATASET_NAME)
            if example.metadata["case_id"] in only
        ]

    results = client.evaluate(
        make_target(settings),
        data=data,
        evaluators=[
            citations_valid,
            found_required_sources,
            answered,
            make_key_points_judge(),
            tool_calls,
            tokens,
        ],
        experiment_prefix=f"{settings.model}",
        metadata={"model": settings.model, "git_commit": git_commit(), "judge": JUDGE_MODEL},
        max_concurrency=2,
    )
    print_summary(
        results,
        [
            "key_points_covered",
            "citations_valid",
            "found_required_sources",
            "answered",
            "tool_calls",
        ],
    )
    print(f"\nExperiment: {results.experiment_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
