# Statement mapping: appendix — methods and data

Run of 2 October 2026. [Summary](summary.md) · [Detailed report](report.md) · [Evidence](evidence.json)

The general method is in the [methodology](../../docs/methodology.md); the decision, answer key and test scope are in the [case spec](../../docs/cases/statement-mapping.md). This appendix records how this run applied them.

## Methods

| Method | Model | Access | Settings |
| --- | --- | --- | --- |
| Jev | typesafe-ai/jev | Vercel AI Gateway, TypeSafe SDK 0.7.2 | One choice question per line; the category descriptions are the answer options |
| GPT-5 mini | openai/gpt-5-mini | Vercel AI Gateway, LangChain structured output | Lowest reasoning setting ("minimal"); provider's default temperature; up to 1,024 output tokens |
| Keyword rules | None | Local code | Fixed patterns on the wording ([rules](../../cases/sec_lines/rules.yaml)); answers only when exactly one keyword rule matches, or a position rule for "other income" lines applies |

All model calls allowed up to three attempts and a 120-second timeout; a call that still failed would count as incorrect. No call failed in this run. Four records were processed at a time.

Both models received the same record and the same candidate categories with their [descriptions](../../cases/sec_lines/case.yaml).

- **GPT-5 mini instruction:** "Match one line from a company's financial statement to one line of a standard template. Use only the supplied record and candidate information. Return the single best template line and a confidence from 0 to 1. Confidence is your estimate of the probability that the selected line is correct. Do not provide rationale."
- **Jev question:** "Which template line does the statement line described in the state belong to?"

Prices used for cost:

<!-- begin prices -->
| Model | Per million input tokens | Per million output tokens | Price date | Source |
| --- | --- | --- | --- | --- |
| GPT-5 mini | $0.25 | $2 | 2026-10-02 | https://ai-gateway.vercel.sh/v1/models |
| Jev | $0.042 | $0 | 2026-10-02 | https://ai-gateway.vercel.sh/v1/models |
<!-- end -->

## Data

Lines come from 21 quarterly archives of the SEC Financial Statement Data Sets (2021 Q1 to 2026 Q1). Only annual reports (10-K) with fiscal years 2021 to 2025 are used, and only income-statement and balance-sheet lines with a single consolidated US-dollar value and a standard us-gaap tag on the template's list.

<!-- begin scope -->
| Step | Lines | Share of all lines |
| --- | --- | --- |
| Income-statement and balance-sheet lines in the selected filings | 1,694,559 | 100.0% |
| In scope: tag on the template list, standard taxonomy, one consolidated USD value | 412,512 | 24.3% |
| After removing repeats of the same wording by the same company | 148,422 | 8.8% |
| Sampled | 2,900 | 0.2% |
<!-- end -->

<!-- begin sample -->
| Property | Value |
| --- | --- |
| Records | 2,900 |
| Categories | 29; 100 records each |
| Companies | 2,304 |
| Fiscal years | 2021, 2022, 2023, 2024, 2025 |
| Statements | 1,500 balance sheet lines; 1,400 income statement lines |
| Consistency checks | 20 records asked twice; 20 with reordered options |
<!-- end -->

**Sampling.** This run took 100 lines from each of the 29 categories. Lines were ordered by a fixed hash of their record ID and the seed 20261001, and the first 100 per category were taken. The repeat and reordered-option checks used 20 lines each, drawn the same way from a 100-line subset spread across categories.

**Answer-key consistency.** "Same company" counts company–wording pairs that appear in at least two filings, once in each filing, and checks whether every filing used the same category. "Two different companies" takes each sampled line whose wording other companies also use on the same statement, and computes the share of those companies that chose the same category; the figure is the average over 2,559 lines. The line's own company is left out.

**Usual and unusual tags.** The usual category for a line is the one most other companies chose for the same wording on the same statement, leaving out the line's own company. Lines whose wording no other company uses form a separate group.

## Results in full

Results with the wording only:

<!-- begin results label_only -->
| Model | Correct | Cost per 1,000 records | Median response |
| --- | --- | --- | --- |
| Jev | 2,732 of 2,900 (94.2%) | $0.054 | 0.63s |
| GPT-5 mini | 2,733 of 2,900 (94.2%) | $0.233 | 1.30s |
<!-- end -->

<!-- begin pairs label_only -->
| Comparison | Both correct | Both incorrect | Only Jev correct | Only the other model correct |
| --- | --- | --- | --- | --- |
| Jev and GPT-5 mini | 2,662 | 97 | 70 | 71 |
<!-- end -->

Correct answers by category, with context:

<!-- begin categories -->
| Category | Records | Jev correct | GPT-5 mini correct |
| --- | --- | --- | --- |
| Other operating items | 100 | 52 | 58 |
| Other non-operating income or expense | 100 | 74 | 88 |
| Total non-operating income or expense | 100 | 93 | 69 |
| Other current liabilities | 100 | 92 | 88 |
| Interest expense | 100 | 98 | 90 |
| Interest income | 100 | 94 | 96 |
| Accrued liabilities | 100 | 98 | 95 |
| Long-term debt | 100 | 97 | 97 |
| Other non-current liabilities | 100 | 97 | 97 |
| Short-term debt | 100 | 98 | 97 |
| Accounts payable | 100 | 98 | 98 |
| Other current assets | 100 | 98 | 98 |
| Other non-current assets | 100 | 97 | 99 |
| Cost of revenue | 100 | 99 | 98 |
| Net income | 100 | 99 | 98 |
| Property, plant and equipment | 100 | 98 | 100 |
| Research and development | 100 | 99 | 99 |
| Revenue | 100 | 99 | 99 |
| Short-term investments | 100 | 99 | 99 |
| Depreciation and amortisation | 100 | 99 | 100 |
| Inventory | 100 | 99 | 100 |
| Operating income | 100 | 100 | 99 |
| Cash | 100 | 100 | 100 |
| Goodwill and intangibles | 100 | 100 | 100 |
| Gross profit | 100 | 100 | 100 |
| Income tax | 100 | 100 | 100 |
| Receivables | 100 | 100 | 100 |
| Selling, general and administrative | 100 | 100 | 100 |
| Total equity | 100 | 100 | 100 |
<!-- end -->

Correct answers by category, wording only:

<!-- begin categories label_only -->
| Category | Records | Jev correct | GPT-5 mini correct |
| --- | --- | --- | --- |
| Other operating items | 100 | 49 | 53 |
| Total non-operating income or expense | 100 | 86 | 48 |
| Other non-operating income or expense | 100 | 57 | 91 |
| Other current liabilities | 100 | 77 | 88 |
| Interest expense | 100 | 97 | 88 |
| Accrued liabilities | 100 | 97 | 91 |
| Other non-current liabilities | 100 | 95 | 95 |
| Short-term debt | 100 | 96 | 96 |
| Cost of revenue | 100 | 97 | 97 |
| Interest income | 100 | 97 | 97 |
| Long-term debt | 100 | 97 | 97 |
| Other current assets | 100 | 98 | 97 |
| Accounts payable | 100 | 98 | 98 |
| Short-term investments | 100 | 97 | 100 |
| Inventory | 100 | 99 | 99 |
| Net income | 100 | 99 | 99 |
| Other non-current assets | 100 | 98 | 100 |
| Depreciation and amortisation | 100 | 99 | 100 |
| Property, plant and equipment | 100 | 99 | 100 |
| Revenue | 100 | 100 | 99 |
| Cash | 100 | 100 | 100 |
| Goodwill and intangibles | 100 | 100 | 100 |
| Gross profit | 100 | 100 | 100 |
| Income tax | 100 | 100 | 100 |
| Operating income | 100 | 100 | 100 |
| Receivables | 100 | 100 | 100 |
| Research and development | 100 | 100 | 100 |
| Selling, general and administrative | 100 | 100 | 100 |
| Total equity | 100 | 100 | 100 |
<!-- end -->

Stated confidence and share correct, with context, in bands of 0.1:

<!-- begin calibration -->
| Model | Stated confidence | Answers | Average stated | Share correct |
| --- | --- | --- | --- | --- |
| Jev | 0.2–0.3 | 2 | 0.28 | 0.0% |
| Jev | 0.3–0.4 | 9 | 0.34 | 44.4% |
| Jev | 0.4–0.5 | 15 | 0.44 | 40.0% |
| Jev | 0.5–0.6 | 42 | 0.54 | 59.5% |
| Jev | 0.6–0.7 | 57 | 0.65 | 68.4% |
| Jev | 0.7–0.8 | 58 | 0.75 | 69.0% |
| Jev | 0.8–0.9 | 106 | 0.85 | 79.2% |
| Jev | 0.9–1.0 | 2,611 | 0.99 | 98.8% |
| Jev | All answers: average gap |  |  | 0.6 points |
| GPT-5 mini | 0.2–0.3 | 1 | 0.24 | 100.0% |
| GPT-5 mini | 0.3–0.4 | 14 | 0.35 | 42.9% |
| GPT-5 mini | 0.4–0.5 | 10 | 0.45 | 40.0% |
| GPT-5 mini | 0.5–0.6 | 23 | 0.56 | 65.2% |
| GPT-5 mini | 0.6–0.7 | 50 | 0.63 | 72.0% |
| GPT-5 mini | 0.7–0.8 | 151 | 0.76 | 80.8% |
| GPT-5 mini | 0.8–0.9 | 692 | 0.85 | 92.9% |
| GPT-5 mini | 0.9–1.0 | 1,959 | 0.93 | 98.8% |
| GPT-5 mini | All answers: average gap |  |  | 6.3 points |
<!-- end -->

## Run record

Run `20261002T232137Z-571ebdd4` produced 18,760 outputs from 28,568 requests, with no failed outputs and no outputs of unknown cost. It followed a completed 58-line run with the same code and settings. The run also executed four combined-scoring variants on a 100-line subset; they are outside the study's methodology, and their results are listed here for completeness.

<!-- begin run -->
| Method | Model | Answers collected | Input | Records | Correct | Requests | Cost per 1,000 records |
| --- | --- | --- | --- | --- | --- | --- | --- |
| decomposed_llm_matrix_small | GPT-5 mini | 2026-10-02 | label only | 100 | 34 | 100 | $0.778 |
| decomposed_llm_parallel_small | GPT-5 mini | 2026-10-02 | label only | 100 | 11 | 2,902 | $6.226 |
| direct_llm_small | GPT-5 mini | 2026-10-02 | label only | 2,900 | 2,733 | 2,900 | $0.233 |
| jev_composite_concurrent | Jev | 2026-10-02 | label only | 100 | 93 | 2,902 | $1.195 |
| jev_composite_fanout | Jev | 2026-10-02 | label only | 100 | 93 | 100 | $0.143 |
| jev_direct | Jev | 2026-10-02 | label only | 2,900 | 2,732 | 2,900 | $0.054 |
| rules_baseline | Rules | 2026-10-02 | label only | 2,900 | 2,024 | 0 | $0.000 |
| decomposed_llm_matrix_small | GPT-5 mini | 2026-10-02 | with context | 100 | 64 | 100 | $0.819 |
| decomposed_llm_parallel_small | GPT-5 mini | 2026-10-02 | with context | 100 | 9 | 2,902 | $6.750 |
| direct_llm_small | GPT-5 mini | 2026-10-02 | with context | 2,900 | 2,762 | 2,900 | $0.251 |
| jev_composite_concurrent | Jev | 2026-10-02 | with context | 100 | 95 | 2,902 | $1.316 |
| jev_composite_fanout | Jev | 2026-10-02 | with context | 100 | 94 | 100 | $0.147 |
| jev_direct | Jev | 2026-10-02 | with context | 2,900 | 2,777 | 2,900 | $0.058 |
| rules_baseline | Rules | 2026-10-02 | with context | 2,900 | 2,024 | 0 | $0.000 |
<!-- end -->

## Reproduce

Predictions and downloaded SEC files stay outside Git. With the run folder present, this command regenerates every generated block, chart and the evidence file without model calls:

```bash
uv run python -m benchmark.cli report --run-id 20261002T232137Z-571ebdd4 --publish-dir reports/statement-mapping-2026-10-02
```
