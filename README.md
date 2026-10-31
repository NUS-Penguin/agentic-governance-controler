# Enterprise AI Workflow Simulation Harness

A lightweight proof-of-concept that simulates one small slice of an
enterprise AI governance workflow:

```
Customer Request
      |
      v
Workflow Agent  --------->  Structured Workflow Object
      |
      v
Governance Agent -------->  Governance Decision
```

This repository is **not** an autonomous agent and **not** a multi-agent
planner. It follows Anthropic's recommended "augmented LLM" pattern: simple,
deterministic, sequential workflows, each stage with a single responsibility
and its own persisted, inspectable output.

It also does **not** implement an evaluation harness, benchmarking, or
deployment recommendations. Those are future, separate components that will
consume this repository's outputs; this repository only produces them.

## Architecture

| Package            | Responsibility                                                                 |
|---------------------|---------------------------------------------------------------------------------|
| `workflow_agent/`   | Parses a (possibly multilingual) enterprise request into a structured JSON object. Never decides approval, risk, or compliance. |
| `governance_agent/` | Given a structured workflow object (never the raw request text), retrieves relevant policy clauses and evaluates likely compliance. |

The two packages never import from each other. `workflow_agent/run.py` is
the only module that wires both agents together for a simulation run, so
either agent can be modified, tested, or replaced independently.

Both agents follow the same internal shape:

```
config/utils (paths, env) -> client (Claude call) -> rag (retrieval)
      -> prompts (templates) -> parser/controller (orchestration + validation)
```

Retrieval in both agents is a dependency-free TF-IDF implementation (no
embeddings, no vector databases) behind a narrow `retrieve(...)` interface,
so it can later be swapped for an embedding-based retriever without changing
any caller.

## Project layout

```
.
├── .env                      # ANTHROPIC_API_KEY (never commit a real key)
├── requirements.txt
├── workflow/                 # CSV inputs consumed by the Workflow Agent
│   ├── workflow_cases.csv        # batch simulation input (request_text per row)
│   ├── workflow_context.csv      # glossary / terminology snippets for retrieval
│   ├── workflow_templates.csv    # example request_type templates for retrieval
│   └── sample_requests.csv       # multilingual example requests (documentation/testing)
├── policies/                 # JSON policy documents (source of governance truth)
│   └── SGModelAIGovFramework2.json   # IMDA Model AI Governance Framework (2nd ed.)
├── workflow_agent/
│   ├── config.py      # env/paths/model configuration
│   ├── client.py       # Anthropic SDK wrapper
│   ├── parser.py        # request text -> ParsedWorkflow
│   ├── rag.py            # TF-IDF retrieval over workflow/ CSVs
│   ├── prompts.py         # system/user prompt templates
│   ├── models.py           # Pydantic schema (ParsedWorkflow)
│   ├── workflow.py          # single-request orchestration + output saving
│   ├── utils.py               # CSV/JSON/logging helpers
│   └── run.py                  # CLI entry point; wires in governance_agent
└── governance_agent/
    ├── client.py        # Anthropic SDK wrapper (independent of workflow_agent)
    ├── controller.py      # retrieval + reasoning orchestration
    ├── rag.py               # TF-IDF retrieval over flattened policy clauses
    ├── policy_loader.py      # flattens policies/*.json into retrievable clauses
    ├── prompts.py              # system/user prompt templates
    ├── models.py                # Pydantic schema (GovernanceDecision)
    └── utils.py                  # env/paths config + JSON helpers

outputs/            # created automatically; one of each per request_id
├── parsed/{id}.json              # ParsedWorkflow produced by the Workflow Agent
├── retrieved/{id}_workflow_context.json   # context retrieved during parsing
├── retrieved/{id}_policy_context.json     # policy clauses retrieved for governance
├── governance/{id}.json          # GovernanceDecision
└── logs/run_log.csv              # single, append-only audit trail (one row per stage per run)
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Edit `.env` and set a real key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

**No API key configured?** Both agents' `client.py` detect a missing or
placeholder `ANTHROPIC_API_KEY` and, instead of raising or calling the
network, return a deterministic default stub response matching their output
schema (`parser_confidence: 0.0`, `automation_level: "UNKNOWN"`, `tier:
"UNKNOWN"`, `approved: false`, no flagged policies). This lets the full
pipeline run end-to-end — CSV loading, retrieval, prompt building,
validation, and output saving — for smoke testing without API access. A
warning is printed to the console whenever this fallback is used.

Optional overrides (all have sensible defaults):

```
ANTHROPIC_MODEL=claude-haiku-4-5        # default model for both agents
WORKFLOW_AGENT_MODEL=...                # override just the Workflow Agent's model
GOVERNANCE_AGENT_MODEL=...              # override just the Governance Agent's model
ANTHROPIC_MAX_TOKENS=1024
RETRIEVAL_TOP_K=5
```

## Running a simulation

Batch mode — processes every row of `workflow/workflow_cases.csv`:

```powershell
.venv\Scripts\python -m workflow_agent.run
```

Single ad-hoc request:

```powershell
.venv\Scripts\python -m workflow_agent.run --request "Deploy Copilot 但是 keep manual approval"
```

Each run prints a one-line summary per request and writes the full
intermediate and final outputs under `outputs/`.

Every simulation execution also appends rows to a single, shared
`outputs/logs/run_log.csv` audit trail (columns: `run_id`, `request_id`,
`timestamp`, `stage`, `message`). `run_id` is a fresh unique id generated for
every call to `simulate_request`, so re-running the same `request_id`/case
(e.g. re-running the batch, or a `--request-id` that matches a previous run)
still produces distinguishable rows rather than overwriting history.

## Design notes / constraints

- **No hallucination policy**: both agents are instructed to return `null` /
  `"UNKNOWN"` rather than guess when information is missing or policy
  evidence is insufficient.
- **Policies are the only source of truth**: `governance_agent/policy_loader.py`
  only restructures the existing JSON in `policies/` into flat, retrievable
  clauses — it never adds or infers regulatory text. Every `policy_id` the
  Governance Agent cites must come from a clause that was actually retrieved
  and shown to the model.
- **No evaluation, no metrics, no benchmarking**: this repository only
  simulates workflow execution and governance review; it intentionally does
  not compare outcomes, score accuracy, or recommend deployment.

## Future extensibility (not implemented here)

This repository is structured so a separate evaluation/benchmarking
repository can later consume `outputs/` (parsed workflows, retrieved
context, governance decisions) to add:

- Expected-outcome comparison and metrics
- Simulation-run aggregation across many cases
- Prompt regression testing / multi-model evaluation
- Deployment recommendations

None of this is implemented here, and adding it should require no changes
to `workflow_agent/` or `governance_agent/`.
