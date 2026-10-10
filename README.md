# research-agent

[![CI](https://github.com/Ashlyn303/research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ashlyn303/research-agent/actions/workflows/ci.yml)

A research assistant agent that searches PubMed, reads abstracts, and writes a cited summary answering a scientific question. Built with [LangGraph](https://github.com/langchain-ai/langgraph) / LangChain and Claude, with tracing in [LangSmith](https://smith.langchain.com).

```
$ uv run agent.py "What are recent approaches to de novo protein design?"

# Recent Approaches to De Novo Protein Design
## 1. Diffusion models for binder design
- RFdiffusion-based binder generation now reaches previously intractable targets ... (PMID 40739343)
...
```

## How it works

The agent runs a tool-calling loop: Claude decides what to search, calls the tools, reads the results, and repeats until it can answer.

| Tool            | What it does                                                                    |
| --------------- | ------------------------------------------------------------------------------- |
| `search_pubmed` | Searches PubMed via NCBI E-utilities, returns titles, journals, years and PMIDs |
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
uv run agent.py "your research question"
```

## Development

```bash
uv run pytest          # tool tests with fake PubMed responses (no network or API keys)
uv run ruff check .    # lint
uv run ruff format .   # format
```

GitHub Actions runs lint, format check and tests on every push and pull request.

## Problems solved along the way

- **Safety-classifier false positives on biology questions.** A plain question about protein design was declined (`stop_reason: refusal`, category `bio`). The agent now enables Anthropic's server-side fallback, so a declined request is retried on a fallback model within the same call, and a final refusal is reported clearly instead of printing an empty answer.
- **NCBI rate limits.** Claude issues tool calls in parallel, which exceeded NCBI's 3 requests/second limit and crashed the run. Requests are now throttled with a shared lock, retried on HTTP 429, and tool errors are returned to the model rather than raised.

## Roadmap

- [ ] Sort PubMed results by relevance
- [ ] Rebuild as an explicit LangGraph `StateGraph` (search → read → "enough evidence?" → summarize)
- [ ] Human-in-the-loop approval before reading full papers
- [ ] Save summaries to an Obsidian vault
- [ ] Evaluation set of research questions with expected key points
