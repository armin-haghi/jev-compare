# Jev Evaluation: Financial Statement Line Mapping

Source: https://app.notion.com/p/3ec785996df481d3898adc68e3049fb2?pvs=204

This README preserves the parent evaluation plan below. The implementation uses **29 categories**, separating total non-operating income from other non-operating income; see [study review](docs/review.md). Python 3.12 and Vercel AI Gateway are the build defaults. Setup and run commands follow the source plan.

Live validation: the GPT-5 mini plus Jev smoke completed 354 outputs with zero final failures, at $0.2862 in estimated list-price cost. The 31-test suite passes. See [validation evidence](docs/smoke-validation.json); this smoke establishes integration, not comparative model quality.

**What:** Evaluation plan for Jev, TypeSafe's decision model, against conventional LLM workflows on repeated finance data decisions. The aim is to find the kind of decision where Jev is the better building block, not to replace LLMs in general.
**Status:** Case 1 (mapping company financial-statement lines to a standard template, using public SEC data) agreed on 2 Oct 2026 and specified in the build brief below. Earlier ESEF framing retired.
**Next step:** Hand the build brief to a coding agent. Run the small profile first.
# Objective: find where Jev beats LLMs
Jev reads text or structured data and answers a fixed question with one of a fixed list of options, a probability for each option, and a confidence number. It writes no explanation. TypeSafe positions it as a component inside ordinary software: code owns the workflow and the rules, and Jev supplies the small judgments the code cannot make, such as which category a messy record belongs to.
This evaluation tests whether that component beats a conventional LLM call on the decisions a finance data-management team makes thousands of times: matching, classifying and mapping records that arrive with inconsistent wording.
Reference: [TypeSafe: How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)
## Hypothesis: Jev wins on bounded, repeated decisions
Jev should do well when:
- the answer comes from a fixed list;
- the same decision repeats across many records;
- several separate clues contribute, and code can combine them;
- the confidence number is reliable enough to decide which answers need a person.
The comparison is against four alternatives on the same records: a rules baseline (keyword and position rules, no model), a small LLM, a frontier LLM, and Jev. The LLMs run two ways: one direct call, and a decomposed version that scores clues separately and lets code combine them, which is Jev's own pattern.
# Case 1: map statement lines to a template
Every US listed company files annual financial statements with the SEC. Each line on those statements carries two things: the company's own wording, and a standard tag the company attached to say what the line is. The tag is public but, in this test, hidden from the model.
**The question:** given one line as the company wrote it, which of 28 standard template lines is it?
**The answer key:** the company's own tag, mapped to a template line.
## How the test works
1. Download the SEC tables that hold every statement line, its wording and its tag.
2. Build one record per line and hide the tag.
3. Ask each system the same question: which template line is this?
4. Reveal the tag and score every answer.
5. Compare the systems on accuracy, cost, speed, repeatability, and whether their confidence separates right answers from wrong ones.
The run starts small, a few hundred records, to prove the mechanism, then moves to the full set for results.
## Example: one wording, two answers
Real lines from FY2024 annual reports. Both companies wrote "Other income, net". The neighbouring lines decide what it is.
| Company | Lines as filed, in order | Template line | Why |
| --- | --- | --- | --- |
| NETGEAR | Income (loss) from operations 12,216 → Other income, net 12,672 → Income (loss) before income taxes 24,888 | Total non-operating income | The only line between operating income and pre-tax income, so it includes interest |
| Veru | Operating loss → Interest expense 607,470 → Other income, net 861,619 → Total non-operating income (expenses) (160,928) → Loss before income taxes | Other non-operating income | A component listed beside interest expense, under a separate total |
| SITE Centers | Under the heading "Revenues from operations": Fee and other income 8,181 | Revenue | "Other income" under a revenue heading is revenue |
## Why this case is hard enough
- **Close neighbours.** The 28 template lines sit a few rows apart within one statement. "Accrued expenses and other current liabilities" fits two lines that share the same section, sign and period; wording and position must separate them.
- **Measured ambiguity.** Thousands of companies use the same wording. Where they attach different tags to it, the data itself marks the label as ambiguous and records how the companies split. Jev's probabilities can be checked against that split.
- **Rules first.** A keyword-and-position baseline runs before any model. Every method is scored on the records the baseline gets wrong, which is where a model earns its place.
## Why it resembles real work
Portfolio companies and borrowers send management accounts with their own line wording. Analysts map those lines into a fixed template before any analysis. The decision, the ambiguity and the volume are the same as in this case.
## Success: the pass rule
Jev passes when its accuracy is within 2 points of the best LLM, on enough records that the gap is not chance (the statistical test is in the build brief), and at least one of the following holds:
- cost per 1,000 records at most one fifth of that LLM's;
- higher accuracy at 80% coverage, when each method sets aside its least confident fifth of answers.
The benchmark also reports failure rate (calls that return nothing usable), repeatability across runs, and latency, so the result reads as an engineering comparison rather than an accuracy table alone.
# Later cases: same harness, new question
The harness is built so a new case replaces case 1 without changing the runner, methods or metrics.
| Case | Question | Answer key | Example |
| --- | --- | --- | --- |
| 2. Entity matching | Is this reported name the same legal entity as this register record? Yes or no. | The legal entity identifier (LEI) a fund reported alongside the name | "HCA, Inc., 3.50%, 9/1/30" as reported by a fund, against the register's HCA Healthcare Inc. (the parent) and HCA Inc. (the subsidiary that issues the bonds) |
| 3. Loan type | What type of loan is this: first lien, second lien, unitranche, subordinated, preferred equity, common equity, other? | The lending fund's own type label, mapped to the fixed list | Doxim, Inc., L + 6.00%, 1.00% floor, matures 02/28/24, filed by Goldman Sachs BDC as "1st Lien/Last-Out Unitranche" |
# Outputs: evidence, summary, chart
- A benchmark run with record-level predictions, so any aggregate can be recomputed and any individual decision inspected.
- A management summary file with the plain-words case description, counts, results by method and by slice, the pass-rule outcome, cost and latency, and representative examples.
- The headline chart: share of records a system decides on its own (x axis) against its error rate on those records (y axis), one line per method.
# Build brief
The sub-page below specifies repository structure, data retrieval, the 28-line template, method implementations, metrics, result schemas, commands and acceptance checks, so a coding agent can build the benchmark without choosing experiment semantics.
[Build Brief: Reusable Jev Benchmark](https://app.notion.com/p/3ec785996df481a7b824fde702c5614d)

## Python runs the benchmark

Use installed Python 3.12 with [uv](https://docs.astral.sh/uv/getting-started/installation/). Dependencies are pinned in uv.lock and installed in the project .venv.

```bash
uv sync --locked
cp .env.example .env
uv run pytest
uv run python -m benchmark.cli demo
```

The demo uses synthetic data and local fake responses. Its 160 prediction rows validate execution and reporting; they measure no model quality.

## Vercel serves all three models

Set AI_GATEWAY_API_KEY and SEC_USER_AGENT in .env. The SEC header must contain your requester name and real contact email. Credentials are read at runtime and excluded from Git and run configuration.

| Role | Configured model | Route |
| --- | --- | --- |
| Small language model | openai/gpt-5-mini | Vercel chat API |
| Frontier language model | anthropic/claude-sonnet-4.6 | Vercel chat API |
| Jev decision model | typesafe-ai/jev | Vercel TypeSafe-compatible API |

Model names, temperature settings and execution limits live in config/experiments/sec_lines.yaml. Changing a model requires a matching dated entry in config/pricing.yaml. OpenAI and Anthropic can also be called directly by changing provider and supplying the corresponding provider key. The TypeSafe direct route uses TYPESAFE_API_KEY; it is optional.

Sources: [Vercel TypeSafe API](https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe), [model catalog and prices](https://ai-gateway.vercel.sh/v1/models), [TypeSafe SDK](https://github.com/typesafe-ai/typesafe-sdk-python).

## Preparation preserves source evidence

```bash
uv run python -m scripts.fetch_sic
uv run python -m benchmark.cli prepare --case sec_lines
uv run python -m benchmark.cli inspect --case sec_lines
uv run python -m benchmark.cli plan --experiment config/experiments/sec_lines.yaml --profile small
```

The industry-list command pins the SEC Standard Industrial Classification descriptions in cases/sec_lines/sic_codes.json. Commit that file before inference. Preparation downloads 21 quarterly archives from 2021 Q1 through 2026 Q1, selects annual reports for fiscal years 2021–2025, and writes eligibility, exclusions, observed label distributions, mapping-review candidates and source hashes under data/processed/sec_lines/. Archives remain under data/raw/sec_lines/. The complete corpus requires several gigabytes of disk space.

Preparation fetches the industry list automatically when it is absent, so the separate industry-list command is optional.

Mappings and rules are established before benchmark answers are inspected. The inspect command reveals references for data auditing; it is not a prompt-tuning workflow. Mapping-review candidates require an explicit decision and a new preparation before freezing.

## Smoke precedes paid study runs

```bash
# Replace each amount with an approved spending limit.
uv run python -m benchmark.cli smoke --experiment config/experiments/sec_lines_smoke.yaml --records-per-line 1 --budget-usd 1
uv run python -m benchmark.cli run --experiment config/experiments/sec_lines_economy.yaml --profile small --budget-usd 1
uv run python -m benchmark.cli run --experiment config/experiments/sec_lines_economy.yaml --profile full --budget-usd 5
uv run python -m benchmark.cli report --run-id RUN_ID
```

The example budgets are limits, not cost forecasts. The economy configuration uses GPT-5 mini and Jev across 58 prerequisite records, then 2,900 main records and 100 composite records, with four records in flight. Its estimated combined cost is $4.95 using the saved smoke rates; retries and response lengths can change this. Parallel decomposed methods ask two questions per candidate: the original small profile can require approximately 74,000–79,000 calls before retries. The plan command reports the exact workload for the prepared sample. Smoke uses held-out records and caps its composite/repeat/shuffle subset at five records. Full runs require a matching completed small run with successful option-order responses from every method and context regime.

Calls use at most three attempts. Authentication errors stop retries. Record failures and abstentions count as incorrect; unknown billed usage remains unknown. A conservative reservation checks the spending limit before each request, including concurrent requests. List-price cost estimates exclude caching discounts and are not billing invoices.

## Artifacts support independent review

The initial smoke configuration runs GPT-5 mini, Jev and rules. Frontier-model inference is blocked unless the caller explicitly supplies --allow-frontier after authorization; the original sec_lines.yaml configuration will stop without that flag. The economy commands above exclude the frontier tier.

Each results/RUN_ID/ directory contains resolved configuration, case configuration, prompt and pricing snapshots, freeze hashes, dataset provenance, sample IDs, payload examples, provider metadata, an append-only prediction journal, predictions.parquet, metrics.json, metrics.csv, management_summary.json, report.md and two coverage/error SVG charts.

Reports lead with properties of the tested dataset and generate a short verdict from saved evidence. The same dataset summary, verdict, known list-price cost and report path appear after smoke, run, demo and report commands. verdict.json preserves the generated conclusion and predictions hash; regeneration refreshes it automatically. Reports regenerate from saved outputs without provider calls or current case data. Direct methods use the main sample; composite methods use a nested subset. Pairwise comparisons use matched IDs, and the pass rule compares all methods on their common subset. Both row and filer-cluster bootstrap intervals are retained; the pass rule uses the filer-cluster interval.

Calibration measures selected-answer correctness probabilities. Composite margins rank confidence but are not treated as probabilities. Observed label distribution agreement is reported separately. Failed or partial runs and synthetic fixtures do not receive a study pass/fail conclusion.

## Cases own decision semantics

Shared modules under benchmark/ import cases dynamically. A case implements prepare, load_records, build_payload, candidates and is_correct. Rules-enabled cases also expose rules; composite-enabled cases expose metadata_scores. Candidate dictionaries contain id, label, description and template_order. The independent yes/no fixture under tests/fixtures/toy_case exercises the same runner, methods and metrics.

See [review decisions](docs/review.md), [the build brief](docs/build-brief.md), and [build status](docs/progress.md).
