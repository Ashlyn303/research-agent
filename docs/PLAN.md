# research-agent project plan

_Last updated: 2026-10-10. Owner: Ashlyn Chen._

Progress is tracked in [GitHub milestones](https://github.com/Ashlyn303/research-agent/milestones). This document explains the goals, design decisions, order of work and how we work. Update it when a decision changes the plan.

## 1. Goal

A **learning and research assistant for science, technology and AI engineering**: it helps me learn new topics and research them in depth, answers with cited, verifiable sources, remembers context within a session, and turns sessions worth keeping into a connected knowledge base in Obsidian and Zotero.

Topics I'll use it for include de novo protein design, AI agents, LLMs and AI engineering, basic biology and statistics, and hands-on engineering I study for fun: electronics and electrical engineering, PCB design, microcontrollers (e.g. ESP32) and mechanics. Any science or tech topic is in scope.

The project serves two purposes, in this order:

1. **Portfolio:** show production-grade agent engineering (measured quality, explicit agent design, testing, CI, security, documentation).
2. **Daily use:** the tool I actually use to learn and research science and tech topics.

### Success criteria for v1.0

| Area | Criterion |
|---|---|
| Quality | ~20 evaluation questions with recorded scores; every change to prompts, models, tools or the graph is compared against the previous scores |
| Trust | Every citation in an answer refers to a source the agent actually retrieved |
| Design | Explicit LangGraph `StateGraph` with typed state, a research/learning router, sessions and a human review step |
| Sources | PubMed and arXiv, plus open-access full text and preprints |
| Knowledge base | Session notes and key paper notes in Obsidian; key papers saved to Zotero |
| Access | CLI, web interface, MCP server for Claude Code / Claude Desktop, weekly digest |
| Engineering | CI (lint, format, types, tests), pre-commit secret scanning, branch protection, Dependabot |
| Cost | Stays within **$20/month** in API credits |
| Docs | README with architecture diagram and demo, design decision records, v1.0.0 release, project write-up |

### Out of scope for v1.0

Everyday questions outside science and technology (Claude itself is better for those), multi-user hosting, paid databases, clinical or medical advice, fine-tuning models.

## 2. Where we are

**M0: Foundations (done)**

- Working agent: PubMed search and abstracts, Claude with refusal fallback, LangSmith tracing
- `src/research_agent/` package with validated config and `research-agent` CLI (#2)
- Relevance-sorted search with a `min_year` filter (#3)
- CI, pre-commit (ruff, gitleaks), Dependabot, branch protection, MIT license (#1)

## 3. Design

### Two kinds of questions

| Path | Example | What the agent does |
|---|---|---|
| **Research** | "What are recent approaches to de novo binder design?" | Searches PubMed/arXiv, reads papers, answers with citations |
| **Learning** | "How do diffusion models work?", "t-test vs Mann-Whitney?", "How does LangGraph checkpointing work?" | Explains step by step, then gives a few sources for further reading (papers, reviews, official documentation) |

A router at the start of the graph decides the path.

### Sessions

```
start a session ──► ask many small questions (nothing saved; the agent remembers context)
                         │
                    "wrap up"
                         ▼
        agent drafts ONE session summary + list of key papers
                         ▼
     I review: edit the summary, untick papers I don't want
                         ▼
   save ──► Obsidian: session note (+ notes for key papers)
        └─► Zotero: only the papers I kept, in a "Research Agent" collection
```

### Obsidian and Zotero rules

**Zotero holds the papers; Obsidian holds my knowledge map.**

- **Obsidian** (#8)
  - The agent writes only inside `Research Agent/` and never edits or deletes my other notes.
  - One **session note** per wrapped-up session: what I explored, what I learned (with citations), open questions, key papers, tags.
  - **Paper notes** only for papers in the approved summary. Each is created once and reused, and links to every session that cites it, so papers shared across sessions connect the graph view.
- **Zotero** (#30)
  - Only papers in the approved summary.
  - Check for duplicates by DOI/PMID first.
  - Added to a `Research Agent` collection, tagged with the topic and `to-read`.
  - Linked both ways with Obsidian. Never edits or deletes existing items.
- **Nothing is saved without my review** (#7).

### Tools vs graph steps

Rule: **if it must always happen, it is a graph step; if the model decides, it is a tool.**

| Tools (Claude decides) | Graph steps (always run) |
|---|---|
| `search_pubmed`, `search_arxiv`, `get_papers` (batch); later full text and related papers | routing, citation check, answer formatting, cost tracking, wrap-up, review |

### Target architecture

```
CLI / web UI / MCP server / weekly schedule
        │
        ▼
LangGraph StateGraph (checkpointer = sessions)
  router ─┬─► research: agent ⇄ tools ─► citation check ─► structured answer
          └─► learning: explanation + further reading ─► structured answer
  "wrap up" ─► session summary ─► [my review] ─► Obsidian + Zotero
        │
        ▼
Sources: PubMed · arXiv · (M3) PubMed Central full text · preprints · Semantic Scholar
Quality: LangSmith traces (tagged) · datasets and experiments · feedback · cost tracking
```

## 4. Milestones

Estimates assume 3–5 hours per week. Each milestone ends with something working and merged.

### M1: Measure (weeks 1–2, ~8 hours)

**Why first:** later changes (the new graph, new sources) can quietly make answers worse. Measuring first means every later PR can show scores before and after.

| Issue | Work |
|---|---|
| #5 | Eval harness: first 5 questions (protein design, AI/LLMs, basic biology, statistics, plus one with no evidence), LangSmith dataset and experiments, automatic checks plus an LLM judge, manual GitHub workflow, baseline |
| #15 | Trace tags (model, prompt version, git commit) and cost tracking; Sonnet for development |
| #6 | Type checking in CI |

**Done when:** one command produces scores and cost for the current agent, and the baseline is in the README.

### M2: MVP, v0.2.0 (weeks 3–8, ~20 hours)

The **minimum viable product**: the smallest version that is truly useful. Ask questions in a session and get structured, cited answers I can trust.

| Issue | Work |
|---|---|
| #4 | Own `StateGraph`: research/learning router, structured answer model, step limit, prompts in files |
| #24 | Batch `get_papers` tool |
| #25 | arXiv search |
| #19 | Citation check on every answer |
| #26 | Sessions with a checkpointer; interactive CLI |
| #27 | Streaming progress in the CLI |
| #28 | 👍/👎 feedback saved to LangSmith |
| #29 | Graph tests with a scripted fake model |
| #9 | Design decision records |

**Done when:** all eval questions score at least as well as the M1 baseline, citation validity is 100%, and `v0.2.0` is tagged.

### M3: More sources (weeks 9–11, ~12 hours)

| Issue | Work |
|---|---|
| #16 | Common source interface; PubMed Central / Europe PMC full text |
| #17 | bioRxiv/medRxiv preprints, labeled as not peer-reviewed |
| #18 | Semantic Scholar citation counts and related papers |

Grow the eval set to ~20 questions, including cases from 👎 feedback.

### M4: Knowledge outputs (weeks 12–14, ~10 hours)

| Issue | Work |
|---|---|
| #7 | "Wrap up" a session and review it (LangGraph interrupt) |
| #8 | Obsidian session notes and key paper notes |
| #30 | Save key papers to Zotero |

**Done when:** a real session goes from questions to an approved Obsidian note and Zotero items, following the rules above.

### M5: Access & automation (weeks 15–17, ~10 hours)

| Issue | Work |
|---|---|
| #31 | MCP server for the literature tools (use them in Claude Code / Claude Desktop) |
| #20 | Streamlit web interface (also the demo) |
| #21 | Weekly digest on GitHub Actions with a spend cap |

### M6: v1.0 (weeks 18–19, ~6 hours)

| Issue | Work |
|---|---|
| #22 | Architecture diagram, demo, CHANGELOG, `v1.0.0` release, project write-up |

### Timeline

| Weeks (from Oct 12, 2026) | Milestone |
|---|---|
| 1–2 | M1: Measure |
| 3–8 | M2: MVP (v0.2.0) |
| 9–11 | M3: More sources |
| 12–14 | M4: Knowledge outputs |
| 15–17 | M5: Access & automation |
| 18–19 | M6: v1.0 (target: late February 2027) |

If a milestone runs over, move the dates rather than skipping the "done when" checks. Easiest to trim: #18 (Semantic Scholar) and #21 (digest) can move after v1.0.

## 5. Testing and evaluation

| Layer | What it checks | Cost | When |
|---|---|---|---|
| Unit tests | Tool parsing, retries, config, CLI | Free | Every commit (CI) |
| Live API tests (`@pytest.mark.live`) | Real PubMed/arXiv responses still parse | Free, needs network | Weekly or manually |
| Graph tests | Routing and graph logic with a scripted fake model | Free | Every commit (CI) |
| Evals | Answer quality with real Claude | ~$1–2 per run on Sonnet | Before merging changes to prompts, models, tools or the graph |

**Eval case format** (`evals/cases.yaml`):

```yaml
- id: rfdiffusion-basics
  category: research          # research | learning | no-evidence | out-of-scope
  topic: protein-design       # protein-design | ai-llm | biology | statistics
  question: "What is RFdiffusion and what can it design?"
  must_retrieve: ["37433327"] # landmark sources a good search should find
  key_points:
    - "Fine-tunes RoseTTAFold as a denoising diffusion model on protein backbones"
    - "Designs binders, symmetric oligomers and motif scaffolds"
```

**Scoring:**
- **Automatic checks:** cited sources were retrieved, `must_retrieve` found, correct path chosen, no refusal, cost and tool calls.
- **LLM judge (Haiku):** key-point coverage against a rubric.

Questions are written by me in my own words. Start with 5, check that the scores match my own judgment, then grow.

## 6. How we work

### Per issue

1. Pick the next issue in the current milestone.
2. Branch from up-to-date `main`: `feat/…`, `fix/…`, `refactor/…`, `docs/…` or `chore/…`.
3. Small commits; pre-commit runs ruff and the secret scanner on each one.
4. `uv run pytest`. For changes to prompts, models, tools or the graph, also run the evals and note scores.
5. Open a PR: what changed, how it was tested (eval scores and cost where relevant), `Closes #N`.
6. CI must pass. I review the diff, then squash and merge.

### Definition of done

- Tests cover the new behavior, and CI passes
- README or docs updated if usage changed
- Eval scores not worse than before (from M1 onward), or the PR explains the trade-off
- No secrets in code; new settings documented in `.env.example`

### Weekly routine (15 minutes)

- Check the [milestones page](https://github.com/Ashlyn303/research-agent/milestones)
- Check API spend in the Anthropic console against the $20/month budget
- Review and merge or close Dependabot PRs
- Pick next week's issue(s); update this plan if priorities changed

## 7. Budget rules ($20/month)

| Use | Model | Rough cost |
|---|---|---|
| Development runs | `claude-sonnet-5-5` | ~$0.05 per question |
| Evals (5–20 questions) | `claude-sonnet-5-5` + Haiku judge | ~$0.50–2 per run |
| Final checks before a milestone ends | `claude-opus-5-5` | ~$0.10–0.25 per question |
| Weekly digest | `claude-sonnet-5-5` | ~$0.50–1 per month |

Spend limit set in the Anthropic console, auto-reload off. Unit and graph tests never call the API.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Safety-classifier false positives on biology questions | Server-side fallback (done); track refusal rate in evals |
| Hallucinated or wrong citations | Citation check (#19) and eval scoring |
| Cluttered Obsidian vault or Zotero library | Session-level saving only, own folder/collection, review before saving, duplicate checks |
| External API limits (NCBI, arXiv, Europe PMC, Semantic Scholar) | Shared rate-limited client, retries, tests with fake responses |
| LangChain/LangGraph API changes | Pinned versions in `uv.lock`; Dependabot PRs tested by CI and evals |
| Cost overruns | Sonnet for development, spend limit, per-run cap for the digest |
| Scope creep | New ideas become issues in a later milestone, not part of the current PR |

## 9. Decisions log

| Date | Decision |
|---|---|
| 2026-10-10 | LangGraph + LangChain with Claude; LangSmith for tracing |
| 2026-10-10 | Server-side refusal fallback after a `bio` false positive on a protein design question |
| 2026-10-10 | Repository lives outside Dropbox (`~/projects`); GitHub is the backup |
| 2026-10-10 | Relevance sort plus `min_year` filter instead of date sort |
| 2026-10-10 | Evals before new features (M1 first) |
| 2026-10-10 | Scope: learning and research assistant for any science, technology and AI engineering topic, with two paths (learning, research) |
| 2026-10-10 | MVP tools: `search_pubmed`, `search_arxiv`, batch `get_papers`; structured answers |
| 2026-10-10 | Save per session, not per question: one Obsidian session note; Zotero only for the summary's key papers, after review |
| 2026-10-10 | Own literature tools in Python; MCP used to expose them (M5), not to replace them |

Longer explanations go into design decision records in `docs/adr/` (#9).
