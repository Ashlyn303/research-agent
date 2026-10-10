# research-agent project plan

_Last updated: 2026-10-10. Owner: Ashlyn Chen._

Progress is tracked in [GitHub milestones](https://github.com/Ashlyn303/research-agent/milestones). This document explains the goals, the order of work and how we work. Update it when a decision changes the plan.

## 1. Goal

Build a research assistant agent that answers biology research questions with cited, verifiable summaries of the literature.

The project serves two purposes, in this order:

1. **Portfolio:** show production-grade agent engineering (measured quality, explicit agent design, testing, CI, security, documentation).
2. **Daily use:** a tool I actually use for my own literature research.

### Success criteria for v1.0

| Area | Criterion |
|---|---|
| Quality | An evaluation set of ~20 research questions with recorded scores; every change to prompts, models or tools is compared against the baseline |
| Trust | Every citation in an answer refers to a paper the agent actually retrieved |
| Design | The agent is an explicit LangGraph `StateGraph` with typed state and a human approval step |
| Sources | PubMed abstracts, open-access full text and preprints |
| Outputs | Command line, web interface and Obsidian notes |
| Automation | A weekly digest runs unattended on GitHub Actions |
| Engineering | CI (lint, format, types, tests), pre-commit secret scanning, branch protection, Dependabot |
| Cost | Stays within **$20/month** in API credits |
| Docs | README with architecture diagram and demo, design decision records, v1.0.0 release, project write-up |

### Out of scope for v1.0

Multi-user hosting and accounts, paid databases (Scopus, Web of Science), clinical or medical advice use, fine-tuning models.

## 2. Where we are

**M0: Foundations (done)**

- Working agent: PubMed search and abstracts, Claude with refusal fallback, LangSmith tracing
- `src/research_agent/` package with validated config and `research-agent` CLI (#2)
- Relevance-sorted search with a `min_year` filter (#3)
- CI, pre-commit (ruff, gitleaks), Dependabot, branch protection, MIT license (#1)

## 3. Architecture

Today:

```
CLI ──► prebuilt agent loop (create_agent) ──► Claude ──► tools: search_pubmed, get_abstract
                                                              │
                                                    LangSmith traces
```

Target for v1.0:

```
CLI / web UI / weekly schedule
        │
        ▼
LangGraph StateGraph
  plan queries ─► search sources ─► [human approval] ─► read papers ─► enough evidence? ─┐
        ▲                                                                  │ no          │ yes
        └──────────────────────────────────────────────────────────────────┘             ▼
                                                                    write answer ─► verify citations
        │
        ▼
Sources: PubMed · PubMed Central full text · preprints · Semantic Scholar
Outputs: terminal · web page · Obsidian note · digest file
Quality: LangSmith traces · eval set · cost tracking
```

## 4. Milestones

Time estimates assume 3–5 hours per week. Each milestone ends with something working and merged.

### M1: Measure (about 2 weeks, ~8 hours)

**Why first:** without measurements, later changes (new graph, new sources) can quietly make answers worse. Building the eval set first means every later PR can show "before vs after" scores.

| Issue | Work |
|---|---|
| #5 | Evaluation set (~20 questions with key points) in LangSmith, scoring script, manual eval workflow, baseline scores |
| #15 | Cost and latency per run; Sonnet for development, Opus for final checks |
| #6 | Type hints and a type checker in CI |

**Done when:** one command (and one manual GitHub workflow) produces scores and cost for the current agent, and the baseline is recorded in the README.

### M2: Own the graph (about 3 weeks, ~10 hours)

| Issue | Work |
|---|---|
| #4 | Replace `create_agent` with an explicit `StateGraph` (plan → search → read → enough evidence? → answer) |
| #7 | Human approval before reading papers (LangGraph interrupt) |
| #9 | Design decision records: why LangGraph, refusal fallback, NCBI rate limiting, graph design |

**Done when:** the new graph scores at least as well as the baseline on the eval set, and the approval step works from the CLI.

### M3: More sources (about 4 weeks, ~15 hours)

| Issue | Work |
|---|---|
| #16 | Common source interface; PubMed Central / Europe PMC full text |
| #17 | bioRxiv/medRxiv preprints, labeled as not peer-reviewed |
| #18 | Semantic Scholar citation counts and related papers |
| #19 | Citation verification, added to eval scores |

**Done when:** answers can draw on full text and preprints, citation validity is 100% on the eval set, and scores are compared to M2.

### M4: Outputs (about 2 weeks, ~8 hours)

| Issue | Work |
|---|---|
| #8 | Save summaries to the Obsidian vault as notes with paper links |
| #20 | Streamlit web interface (also the demo) |

**Done when:** a question asked in the browser produces a cited answer and, optionally, an Obsidian note.

### M5: Automation (about 2 weeks, ~6 hours)

| Issue | Work |
|---|---|
| #21 | Weekly digest on GitHub Actions: topics config, only new papers, spend cap per run |

The digest runs in the cloud, so it cannot write to the local Obsidian vault directly. It writes to a private digest repo or a GitHub issue, which Obsidian can sync from.

**Done when:** the digest has run unattended for two weeks in a row within budget.

### M6: v1.0 (about 2 weeks, ~6 hours)

| Issue | Work |
|---|---|
| #22 | Architecture diagram, demo GIF, CHANGELOG, `v1.0.0` release, project write-up |

**Done when:** the v1.0.0 release is published and the write-up is linked from the README and my resume.

### Timeline

| Weeks (from Oct 12, 2026) | Milestone |
|---|---|
| 1–2 | M1: Measure |
| 3–5 | M2: Own the graph |
| 6–9 | M3: More sources |
| 10–11 | M4: Outputs |
| 12–13 | M5: Automation |
| 14–15 | M6: v1.0 (target: mid-January 2027) |

If a milestone runs over, move the timeline rather than skipping the "done when" checks. M3 is the largest and the easiest to trim: #18 can move after v1.0.

## 5. How we work

### Per issue

1. Pick the next issue in the current milestone.
2. Create a branch from up-to-date `main`: `feat/…`, `fix/…`, `refactor/…`, `docs/…` or `chore/…`.
3. Make small commits. Pre-commit runs ruff and the secret scanner on each one.
4. Run `uv run pytest`. For changes to prompts, models, tools or the graph, also run the eval set and note the scores.
5. Open a PR that says what changed, how it was tested (with eval scores and cost where relevant) and `Closes #N`.
6. CI must pass. Review the diff, then squash and merge.

### Definition of done

- Tests cover the new behavior, and CI passes
- README or docs updated if usage changed
- Eval scores not worse than before (from M1 onward), or the PR explains the trade-off
- No secrets in the code; new settings documented in `.env.example`

### Weekly routine (15 minutes)

- Open the [milestones page](https://github.com/Ashlyn303/research-agent/milestones) and check progress
- Check API spend in the Anthropic console against the $20/month budget
- Review and merge or close Dependabot PRs
- Choose the next week's issue(s); update this plan if priorities changed

## 6. Budget rules ($20/month)

| Use | Model | Rough cost |
|---|---|---|
| Development runs | `claude-sonnet-5-5` | ~$0.05 per question |
| Eval set (20 questions) | `claude-sonnet-5-5` | ~$1–2 per run |
| Final checks before a milestone ends | `claude-opus-5-5` | ~$0.10–0.25 per question |
| Weekly digest | `claude-sonnet-5-5` | ~$0.50–1 per month |

Keep a spend limit set in the Anthropic console and auto-reload off. Unit tests never call the API.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Safety-classifier false positives on biology questions | Server-side fallback (done); track refusal rate in evals |
| Hallucinated or wrong citations | Citation verification (#19) and eval scoring |
| External API limits (NCBI, Europe PMC, Semantic Scholar) | Shared rate-limited client, retries, tests with fake responses |
| LangChain/LangGraph API changes | Pinned versions in `uv.lock`, Dependabot PRs tested by CI and evals |
| Cost overruns | Sonnet for development, spend limit, per-run spend cap for the digest |
| Scope creep | New ideas become issues in a later milestone, not part of the current PR |

## 8. Decisions log

| Date | Decision |
|---|---|
| 2026-10-10 | LangGraph + LangChain with Claude; LangSmith for tracing |
| 2026-10-10 | Server-side refusal fallback after a `bio` false positive on a protein design question |
| 2026-10-10 | Repository lives outside Dropbox (`~/projects`); GitHub is the backup |
| 2026-10-10 | Relevance sort plus `min_year` filter instead of date sort |
| 2026-10-10 | Evals before new features (M1 first) |

Longer explanations go into design decision records in `docs/adr/` (#9).
