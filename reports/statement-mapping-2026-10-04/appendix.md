# Statement mapping: appendix — methods and data

Runs of 4 October 2026. [Summary](summary.md) · [Detailed report](report.md) · [Evidence](evidence.json)

General method: [methodology](../../docs/methodology.md). Decision, answer key and scope: [case spec](../../docs/cases/statement-mapping.md). Dataset: `sec_lines-2900-8bad7b33`.

## Models and settings

| Model | Gateway ID | Settings | Input versions |
| --- | --- | --- | --- |
| [Jev](https://vercel.com/ai-gateway/models/jev) | typesafe-ai/jev (System One name `jev`) | One [choice question](https://docs.typesafe.ai/primitives/choice) per line; category descriptions are the answer options | Wording only; with context |
| [GPT-6 Luna](https://vercel.com/ai-gateway/models/gpt-6-luna) | openai/gpt-6-luna | Reasoning effort none; up to 4,096 output tokens | Wording only; with context |
| [Gemini 3.8 Flash](https://vercel.com/ai-gateway/models/gemini-3.8-flash) | google/gemini-3.8-flash | Reasoning effort low; up to 4,096 output tokens | Wording only; with context |
| [Claude Haiku 4.5](https://vercel.com/ai-gateway/models/claude-haiku-4.5) | anthropic/claude-haiku-4.5 | Reasoning off; up to 4,096 output tokens | With context |
| Keyword rules | None | Fixed patterns on the wording ([rules](../../cases/sec_lines/rules.yaml)); answer only when one rule matches | Wording only; with context |

All models are called through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway). Chat models return a category from the offered list and a confidence from 0 to 1 in a strict JSON format. Each call allows three attempts and a 120-second timeout; four lines are processed at a time per model.

- **Chat model instruction:** "Match one line from a company's financial statement to one line of a standard template. Use only the supplied record and candidate information. Return the single best template line and a confidence from 0 to 1. Choose not_mapped for a total, subtotal or other line that the template does not hold. Confidence is your estimate of the probability that the selected line is correct. Do not provide rationale."
- **Jev question:** "Which template line does the statement line described in the state belong to? Choose not mapped for a total, subtotal or other line that the template does not hold."

<!-- begin prices -->
| Model | Per million input tokens | Per million output tokens | Price date | Source |
| --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | $1 | $5 | 2026-10-04 | https://ai-gateway.vercel.sh/v1/models |
| Gemini 3.8 Flash | $0.75 | $3.75 | 2026-10-04 | https://ai-gateway.vercel.sh/v1/models |
| GPT-6 Luna | $0.1 | $0.5 | 2026-10-04 | https://ai-gateway.vercel.sh/v1/models |
| Jev | $0.042 | $0 | 2026-10-04 | https://ai-gateway.vercel.sh/v1/models |
<!-- end -->

## Data

Source: SEC [Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets), annual reports (10-K) for fiscal years 2021 to 2025, quarterly archives 2021 Q1 to 2026 Q1.

<!-- begin scope -->
| Step | Lines | Share of all lines |
| --- | --- | --- |
| Income-statement and balance-sheet lines in the selected filings | 1,694,559 | 100.0% |
| In scope: a standard tag on the case's lists and one consolidated USD value | 597,580 | 35.3% |
| After removing repeats of the same wording by the same company | 210,738 | 12.4% |
| Sampled | 2,900 | 0.2% |
<!-- end -->

<!-- begin sample -->
| Property | Value |
| --- | --- |
| Records | 2,900 |
| Categories | 30; 14–819 records each |
| Companies | 2,386 |
| Fiscal years | 2021, 2022, 2023, 2024, 2025 |
| Statements | 1,655 balance sheet lines; 1,245 income statement lines |
| Consistency checks | 290 records asked twice; 290 with reordered options |
<!-- end -->

**Sampling.** Lines are ordered by a fixed hash of their record ID and seed 20261001; the first 2,900 form the dataset. Separate hash orders pick the 290 lines asked twice and the 290 asked with reordered options.

**Answer-key consistency.** "Same company" counts company–wording pairs that appear in at least two annual reports, once in each, and checks whether every report used the same category. "Two different companies" takes each sampled line whose wording other companies also use on the same statement, and averages the share of those companies that chose the same category, leaving out the line's own company.

<!-- begin agreement -->
| Comparison | Cases | Same category |
| --- | --- | --- |
| Same company, same wording, different filings | 140,367 | 99.6% |
| Two different companies, same wording | 2,638 sampled records | 96.8% |
<!-- end -->

**Usual and unusual tags.** The usual category for a line is the one most other companies chose for the same wording on the same statement.

## Results in full

With the wording only:

<!-- begin results label_only -->
| Model | Correct | Cost per 1,000 records | Median response |
| --- | --- | --- | --- |
| Jev | 2,753 of 2,900 (94.9%) | $0.059 | 0.58s |
| Gemini 3.8 Flash | 2,825 of 2,900 (97.4%) | $0.658 | 1.88s |
| GPT-6 Luna | 2,789 of 2,900 (96.2%) | $0.082 | 1.45s |
<!-- end -->

<!-- begin pairs label_only -->
| Comparison | Both correct | Both incorrect | Only Jev correct | Only the other model correct |
| --- | --- | --- | --- | --- |
| Jev and Gemini 3.8 Flash | 2,742 | 64 | 11 | 83 |
| Jev and GPT-6 Luna | 2,720 | 78 | 33 | 69 |
<!-- end -->

Correct answers by category, with context:

<!-- begin categories -->
| Category | Records | Jev correct | Claude Haiku 4.5 correct | Gemini 3.8 Flash correct | GPT-6 Luna correct |
| --- | --- | --- | --- | --- | --- |
| Not mapped | 819 | 791 | 790 | 810 | 802 |
| Other non-operating income or expense | 82 | 47 | 75 | 60 | 69 |
| Total equity | 183 | 165 | 179 | 158 | 183 |
| Total non-operating income or expense | 64 | 59 | 36 | 63 | 52 |
| Net income | 185 | 161 | 182 | 185 | 178 |
| Other operating items | 14 | 9 | 10 | 9 | 10 |
| Other current liabilities | 28 | 23 | 24 | 24 | 24 |
| Revenue | 93 | 86 | 91 | 92 | 90 |
| Cost of revenue | 69 | 66 | 66 | 67 | 66 |
| Interest income | 28 | 26 | 24 | 27 | 26 |
| Operating income | 110 | 109 | 107 | 109 | 107 |
| Accounts payable | 69 | 66 | 68 | 68 | 67 |
| Interest expense | 60 | 59 | 59 | 59 | 57 |
| Short-term debt | 39 | 37 | 38 | 38 | 37 |
| Goodwill and intangibles | 105 | 104 | 104 | 104 | 104 |
| Gross profit | 42 | 41 | 41 | 41 | 41 |
| Income tax | 142 | 141 | 141 | 141 | 141 |
| Long-term debt | 31 | 29 | 29 | 31 | 31 |
| Other current assets | 76 | 75 | 75 | 75 | 75 |
| Research and development | 40 | 39 | 39 | 39 | 39 |
| Other non-current liabilities | 56 | 54 | 55 | 56 | 56 |
| Accrued liabilities | 55 | 55 | 54 | 55 | 54 |
| Cash | 99 | 98 | 99 | 99 | 99 |
| Other non-current assets | 65 | 64 | 65 | 65 | 65 |
| Property, plant and equipment | 102 | 102 | 101 | 102 | 102 |
| Depreciation and amortisation | 18 | 18 | 18 | 18 | 18 |
| Inventory | 52 | 52 | 52 | 52 | 52 |
| Receivables | 115 | 115 | 115 | 115 | 115 |
| Selling, general and administrative | 41 | 41 | 41 | 41 | 41 |
| Short-term investments | 18 | 18 | 18 | 18 | 18 |
<!-- end -->

Stated confidence and share correct, with context:

<!-- begin calibration -->
| Model | Stated confidence | Answers | Average stated | Share correct |
| --- | --- | --- | --- | --- |
| Jev | 0.2–0.3 | 3 | 0.25 | 0.0% |
| Jev | 0.3–0.4 | 7 | 0.35 | 85.7% |
| Jev | 0.4–0.5 | 56 | 0.47 | 53.6% |
| Jev | 0.5–0.6 | 94 | 0.54 | 61.7% |
| Jev | 0.6–0.7 | 107 | 0.64 | 71.0% |
| Jev | 0.7–0.8 | 122 | 0.75 | 84.4% |
| Jev | 0.8–0.9 | 280 | 0.85 | 92.9% |
| Jev | 0.9–1.0 | 2,231 | 0.98 | 99.4% |
| Jev | All answers: average gap |  |  | 3.2 points |
| Claude Haiku 4.5 | 0.1–0.2 | 2 | 0.15 | 0.0% |
| Claude Haiku 4.5 | 0.3–0.4 | 3 | 0.35 | 0.0% |
| Claude Haiku 4.5 | 0.4–0.5 | 3 | 0.45 | 0.0% |
| Claude Haiku 4.5 | 0.6–0.7 | 3 | 0.65 | 33.3% |
| Claude Haiku 4.5 | 0.7–0.8 | 84 | 0.74 | 69.0% |
| Claude Haiku 4.5 | 0.8–0.9 | 194 | 0.85 | 82.5% |
| Claude Haiku 4.5 | 0.9–1.0 | 2,611 | 0.95 | 98.7% |
| Claude Haiku 4.5 | All answers: average gap |  |  | 3.4 points |
| Gemini 3.8 Flash | 0.3–0.4 | 2 | 0.32 | 100.0% |
| Gemini 3.8 Flash | 0.4–0.5 | 2 | 0.40 | 50.0% |
| Gemini 3.8 Flash | 0.5–0.6 | 1 | 0.55 | 0.0% |
| Gemini 3.8 Flash | 0.6–0.7 | 1 | 0.65 | 0.0% |
| Gemini 3.8 Flash | 0.7–0.8 | 2 | 0.75 | 100.0% |
| Gemini 3.8 Flash | 0.8–0.9 | 66 | 0.85 | 59.1% |
| Gemini 3.8 Flash | 0.9–1.0 | 2,826 | 0.99 | 98.3% |
| Gemini 3.8 Flash | All answers: average gap |  |  | 1.1 points |
| GPT-6 Luna | 0.4–0.5 | 2 | 0.45 | 50.0% |
| GPT-6 Luna | 0.5–0.6 | 12 | 0.57 | 91.7% |
| GPT-6 Luna | 0.6–0.7 | 25 | 0.66 | 88.0% |
| GPT-6 Luna | 0.7–0.8 | 59 | 0.76 | 78.0% |
| GPT-6 Luna | 0.8–0.9 | 122 | 0.85 | 76.2% |
| GPT-6 Luna | 0.9–1.0 | 2,680 | 0.99 | 98.7% |
| GPT-6 Luna | All answers: average gap |  |  | 0.8 points |
<!-- end -->

## Run record

<!-- begin run -->
| Method | Model | Answers collected | Input | Records | Correct | Requests | Answers with an unpriced failed attempt | Cost per 1,000 records |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chat:google/gemini-3.8-flash | google/gemini-3.8-flash | 2026-10-04 | label only | 2,900 | 2,825 | 2,901 | 1 | $0.658 |
| chat:openai/gpt-6-luna | openai/gpt-6-luna | 2026-10-04 | label only | 2,900 | 2,789 | 2,904 | 4 | $0.082 |
| decision:typesafe-ai/jev | Jev | 2026-10-04 | label only | 2,900 | 2,753 | 2,902 | 2 | $0.059 |
| rules_baseline | Rules | 2026-10-04 | label only | 2,900 | 1,495 | 0 | 0 | $0.000 |
| chat:anthropic/claude-haiku-4.5 | anthropic/claude-haiku-4.5 | 2026-10-04 | with context | 2,900 | 2,796 | 2,900 | 0 | $1.184 |
| chat:google/gemini-3.8-flash | google/gemini-3.8-flash | 2026-10-04 | with context | 2,900 | 2,821 | 2,903 | 3 | $0.735 |
| chat:openai/gpt-6-luna | openai/gpt-6-luna | 2026-10-04 | with context | 2,900 | 2,819 | 2,900 | 0 | $0.090 |
| decision:typesafe-ai/jev | Jev | 2026-10-04 | with context | 2,900 | 2,750 | 2,901 | 1 | $0.063 |
| rules_baseline | Rules | 2026-10-04 | with context | 2,900 | 1,495 | 0 | 0 | $0.000 |
<!-- end -->

Also run on this dataset and stopped to stay within budget, not used: GPT-6 Sol (768 answers, $1.33), Claude Sonnet 5.5 (534 answers, $1.60) and a first Gemini 3.8 Flash run (526 answers, $0.37). Two trials outside the dataset checked access and token use: 30 lines with five models ($0.41) and 10 lines with Claude Haiku 4.5 ($0.03). Qwen 3.8 Flash was left out after 80 of 138 trial requests returned "service unavailable".

## Reproduce

Predictions and SEC downloads stay outside Git; the dataset is in `data/samples/`. With the run folders present, this command regenerates every generated block, chart and the evidence file without model calls:

```bash
uv run python -m benchmark.cli report --dataset sec_lines-2900-8bad7b33 --publish-dir reports/statement-mapping-2026-10-04
```
