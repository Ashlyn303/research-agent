# research-agent

[![CI](https://github.com/Ashlyn303/research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ashlyn303/research-agent/actions/workflows/ci.yml)

A research assistant agent that searches PubMed, reads abstracts, and writes a cited summary answering a scientific question. Built with [LangGraph](https://github.com/langchain-ai/langgraph) / LangChain and Claude, with tracing in [LangSmith](https://smith.langchain.com).

```
$ uv run research-agent "What are recent approaches to de novo protein design?"

# Recent Approaches to De Novo Protein Design
## 1. Diffusion models for binder design
- RFdiffusion-based binder generation now reaches previously intractable targets ... (PMID 40739343)
...
```

## How it works

The agent runs a tool-calling loop: Claude decides what to search, calls the tools, reads the results, and repeats until it can answer.

| Tool            | What it does                                                                    |
| --------------- | ------------------------------------------------------------------------------- |
| `search_pubmed` | Searches PubMed via NCBI E-utilities, sorted by relevance with an optional `min_year` filter; returns titles, journals, years and PMIDs |
| `get_abstract`  | Fetches the abstract for one PMID                                               |

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
cp .env.example .env   # then fill in your keys
```

- `ANTHROPIC_API_KEY`: from [console.anthropic.com](https://console.anthropic.com)
- `LANGSMITH_API_KEY`: optional, from [smith.langchain.com](https://smith.langchain.com), for tracing every step of a run
- `MODEL`: defaults to `claude-opus-5-5`; `claude-sonnet-5-5` costs about half as much

## Usage

```bash
uv run research-agent "your research question"
uv run research-agent -v "your research question"   # also log each tool call
```

## Project layout

```
src/research_agent/
  config.py        settings from environment / .env, validated at startup
  tools/pubmed.py  PubMed search and abstract tools (rate-limited NCBI client)
  agent.py         builds the agent; nothing is created at import time
  cli.py           `research-agent` command
tests/             unit tests with fake PubMed responses and a fake agent
```

## Development

```bash
uv run pytest          # tool tests with fake PubMed responses (no network or API keys)
uv run ruff check .    # lint
uv run ruff format .   # format
```

GitHub Actions runs lint, format check and tests on every push and pull request.

## Evaluation

Five evaluation questions in [`evals/cases.yaml`](evals/cases.yaml) cover research questions (protein design, AI agents), learning questions (biology, statistics) and a trap question about a method that does not exist. Each run is recorded as a LangSmith experiment.

```bash
uv run python -m evals.run --model claude-sonnet-5-5          # all questions
uv run python -m evals.run --cases react-agents               # selected questions
```

Or run the **Evals** workflow by hand from the GitHub Actions tab.

| Score | How it is measured |
|---|---|
| Key points covered | Claude Haiku judges which of the case's key points the answer conveys |
| Citations valid | Share of cited PMIDs/arXiv IDs that the agent actually retrieved |
| Found required sources | Share of the case's `must_retrieve` papers that were retrieved |
| Answered | 0 if the request was declined |

### Baseline (v0.1, prebuilt agent with PubMed only)

| Question | Sonnet 5.5: key points / citations / required sources | Opus 5.5: key points / citations / required sources |
|---|---|---|
| RFdiffusion + ProteinMPNN pipeline | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| ReAct agents | 0.67 / 1.00 / **0.00** | 1.00 / **0.67** / **0.00** |
| Sequence determines structure | **0.40** / 1.00 / - | 0.80 / 1.00 / - |
| Mann-Whitney vs t-test | 1.00 / 1.00 / - | **0.60** / 1.00 / - |
| Nonexistent method (trap) | 1.00 / 1.00 / - | 1.00 / 1.00 / - |
| **Cost for all 5** | **$0.13** (median 16 s per question) | **$0.53** (median 27 s per question) |

What the baseline shows:

- **No arXiv search yet:** neither model could retrieve the ReAct paper. Opus cited it from memory, which the citation check flags as an unretrieved source (#25).
- **Learning questions get literature reviews:** asked why sequence determines structure, the agent searched PubMed and summarized energy-landscape papers instead of explaining the basics (hydrophobic effect, hydrogen bonds, Anfinsen's experiment). The research/learning router (#4) targets this.
- **No hallucinated method:** both models said they found nothing about the made-up method.
- Sonnet costs about a quarter of Opus here and is the default for development and evals.

## Problems solved along the way

- **Safety-classifier false positives on biology questions.** A plain question about protein design was declined (`stop_reason: refusal`, category `bio`). The agent now enables Anthropic's server-side fallback, so a declined request is retried on a fallback model within the same call, and a final refusal is reported clearly instead of printing an empty answer.
- **Fallback blocks broke multi-step runs.** When the fallback ran, `langchain-anthropic` saved the response's `fallback` block with the Python field name `from_` instead of `from`, so the next model call failed with `fallback.from: Field required`. A small agent middleware restores the field name before each model call.
- **An LLM judge that was too strict.** The first baseline gave a correct answer 0 of 4 key points. Combined key points (two claims in one) and a "be strict" instruction caused false failures. Key points are now one idea each, and the judge was checked by re-scoring saved answers: identical scores on repeat runs, and agreement with a Sonnet judge on 8 of 10 answers.
- **NCBI rate limits.** Claude issues tool calls in parallel, which exceeded NCBI's 3 requests/second limit and crashed the run. Requests are now throttled with a shared lock, retried on HTTP 429, and tool errors are returned to the model rather than raised.

## Roadmap

- [x] Sort PubMed results by relevance
- [ ] Rebuild as an explicit LangGraph `StateGraph` (search → read → "enough evidence?" → summarize)
- [ ] Human-in-the-loop approval before reading full papers
- [ ] Save summaries to an Obsidian vault
- [x] Evaluation set of research questions with expected key points
