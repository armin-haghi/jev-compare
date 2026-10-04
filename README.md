# Jev compare

This repository compares Jev, TypeSafe's model that answers a fixed question by choosing from predefined answers, with a conventional language model and programmed rules on repeated finance data-management decisions. Each study reports one case; the methodology applies to other cases.

**Latest study:** statement mapping, run of 2 October 2026 — [summary](reports/statement-mapping-2026-10-02/summary.md), [detailed report](reports/statement-mapping-2026-10-02/report.md), [appendix: methods and data](reports/statement-mapping-2026-10-02/appendix.md).

| Document | Purpose |
| --- | --- |
| [Methodology](docs/methodology.md) | Comparisons, patterns, metrics and how reports are written |
| [Statement mapping case](docs/cases/statement-mapping.md) | Decision, answer key, test scope and decisions for the next run |
| [Backlog](docs/backlog.md) | Open methodology questions |
| [Development notes](docs/development.md) | Problems found in earlier runs and how to avoid them |
| [Archive](docs/archive/) | Original proposal, build brief, design review and build history |

## Setup

Python 3.12 with dependencies pinned in uv.lock. Credentials stay in the ignored .env file.

```bash
uv sync --locked
cp .env.example .env
uv run pytest
uv run python -m benchmark.cli demo
```

The demo uses synthetic responses and makes no model calls. Live runs need AI_GATEWAY_API_KEY and SEC_USER_AGENT (requester name and contact email). Every model is called through the Vercel AI Gateway; changing the model name in the settings file switches to any model the gateway offers, such as Anthropic or Google models.

## Commands

```bash
uv run python -m benchmark.cli prepare --case sec_lines            # download and prepare SEC data
uv run python -m benchmark.cli plan --experiment config/experiments/sec_lines.yaml --profile full
uv run python -m benchmark.cli run --experiment config/experiments/sec_lines.yaml --profile small --budget-usd 1
uv run python -m benchmark.cli report --run-id RUN_ID --publish-dir reports/STUDY   # refresh generated blocks, no model calls
```

Models are listed by name in the settings file: decision models such as `typesafe-ai/jev`, and chat models such as `openai/gpt-5-mini`, `anthropic/claude-sonnet-4.6` or `google/gemini-2.5-flash`. Prices come from the gateway catalog when a run starts.

To add a model to an existing comparison, run the same settings with only the new model listed (and `rules: false`), then combine the runs in one report: `report --run-id FIRST_RUN --run-id NEW_RUN --publish-dir reports/STUDY`. The report refuses runs that tested different records or data.

Paid runs require --budget-usd; spending limits reserve for calls in progress.

Each run writes results/RUN_ID/ with predictions, raw responses, configuration, prices, prompts and an evidence file. The report command refreshes the generated tables and charts in a study's documents from those results. Downloaded data, results and .venv stay outside Git.

## Code

| Path | Role |
| --- | --- |
| benchmark/runner.py | Samples records, calls each method, records answers, usage and cost |
| benchmark/methods/ | One module per method: rules, decision model (Jev), chat model |
| benchmark/metrics.py | Every number the reports use, computed from saved results |
| benchmark/report.py | Fills the generated blocks and charts in a study's documents, from one or more runs |
| cases/sec_lines/ | The statement mapping case: data preparation, template, rules, prompts |

A case implements prepare, load_records, build_payload, candidates, is_correct and rules. The runner and metrics do not depend on the statement mapping case; a synthetic test case checks that.
