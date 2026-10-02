# Build Brief: Reusable Jev Benchmark

Source: https://app.notion.com/p/3ec785996df481a7b824fde702c5614d?pvs=204

**What:** Build brief for a reusable benchmark that compares Jev (TypeSafe's decision model, which returns a typed answer with probabilities instead of text) against conventional LLM workflows on one repeated finance data decision. Case 1 maps lines of US company financial statements to a standard template.
**Status:** Case 1 agreed on 2 Oct 2026 and written in below. All review items closed. Run size and the option-order test are parameters: a small profile proves the mechanism, a full profile produces the results.
**Next step:** Hand this brief to a coding agent. Run the small profile first.
# Goal: compare Jev with LLMs on one decision
Build a benchmark harness that asks the same question of several systems and scores them against a public answer key. The harness is written so that a second case (entity matching, loan-type classification) can replace case 1 without changes to the runner, the method code, the result format, or the metric engine.
**Case 1 in one sentence:** a company's own line on its income statement or balance sheet, such as "Other income, net", must be matched to one of 28 standard template lines, such as "Total non-operating income". The company's own tag on that line, filed with the SEC, says which template line is correct.
## How the test works
1. Download the SEC tables that hold every statement line, its wording and its tag.
2. Build one record per line. Hide the tag. Keep the wording, the statement, the neighbouring lines, the amount's sign and size, and the industry.
3. Ask each system the same question: which of the template lines is this?
4. Reveal the tag and score every answer.
5. Compare the systems on accuracy, cost, speed, repeatability, and how well their confidence separates right answers from wrong ones.
The run starts with a small profile (a few hundred records) to prove the mechanism end to end, then moves to the full profile for results. The small profile must complete, including the option-order test, before the full profile starts.
## Terms: plain definitions
| Term | Meaning |
| --- | --- |
| Filer | A US company that files an annual report (Form 10-K) with the SEC. |
| Line label | The wording a filer prints on one row of its financial statements, for example "Interest and other income, net". |
| Tag | The standard code the filer attaches to that row in its filing, taken from the US GAAP taxonomy, for example NonoperatingIncomeExpense. Every row on the face of the statements carries one. |
| Template line | One of the 28 standard lines the model may pick from. The answer set. |
| Answer key | The template line the filer's tag maps to. Hidden from the model, used for scoring. |
| FSDS | SEC Financial Statement Data Sets: free quarterly tables holding every line label, tag and value from every filing. |
| Jev | TypeSafe's decision model. It takes text or JSON plus a question and returns a choice, a probability for each option, and a confidence number. It writes no explanation. |
| LLM | A conventional large language model such as GPT or Claude, called with a structured-output schema. |
| Confidence | A number from 0 to 1 that a method attaches to its answer. Used to decide which answers a system could accept without review. |
## Decisions: fixed before the build
| Decision | Specification |
| --- | --- |
| Filings | Form 10-K annual reports, fiscal years 2021 to 2025, from the FSDS tables. |
| Statements | Income statement and balance sheet. Cash flow statement is out of scope for this run. |
| Answer set | 28 template lines, 13 for the income statement and 15 for the balance sheet, listed under Template. The model chooses among the lines of the statement the record sits on. |
| Answer key | The filer's tag, mapped to a template line by the config file template.yaml. Lines whose tag is outside the file are excluded. |
| Model input | Line label, statement, the two line labels above and below, sign of the amount, amount as a share of revenue (income statement) or total assets (balance sheet), and the filer's industry code (SIC) with its description. |
| Competing systems | Rules baseline, a small LLM, a frontier LLM, and Jev. The two LLMs each run the direct and the decomposed method. |
| Pass rule for Jev | Accuracy within 2 points of the best LLM (lower bound of a paired bootstrap 95% interval at or above minus 2 points), and at least one of: cost per 1,000 records at most one fifth of that LLM's, or higher accuracy at 80% coverage when each method's least confident answers are set aside. |
| Training | None. No model is fine-tuned. |
| Human review | Not part of the benchmark. |
| Freeze | Prompts, rules, template and configuration are frozen before any benchmark answer is inspected. |
## Sources: pin external dependencies
- [SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/financial-statement-data-sets.html), with the [field documentation](https://www.sec.gov/files/financial-statement-data-sets.pdf). Quarterly ZIP files containing sub.txt (filings), pre.txt (line labels and tags as presented), num.txt (values) and tag.txt (tag definitions and standard labels).
- SEC requires a User-Agent header naming the requester on every download. Set it from configuration.
- [TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python), pin typesafe-sdk==0.7.2.
- [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart), [composite scoring](https://docs.typesafe.ai/patterns/composite-scoring), [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out), [confidence](https://docs.typesafe.ai/confidence).
- [LangChain structured output](https://reference.langchain.com/python/langchain-core/language_models/chat_models/BaseChatModel/with_structured_output).
## Stack: use Python consistently
Use Python 3.11 and uv.
Required direct dependencies:
```plain text
pandas
pyarrow
pydantic
pyyaml
requests
langchain==1.4.0
langchain-openai==1.6.2
langchain-anthropic==1.7.2
typesafe-sdk==0.7.2
```
Development dependency:
```plain text
pytest
```
Commit uv.lock so transitive versions are fixed.
Support openai and anthropic as LLM providers through LangChain init_chat_model. Each run names two conventional models in configuration: a small tier and a frontier tier. Fail fast when a credential is missing.
## Repository: separate framework and case
```plain text
pyproject.toml
README.md
.env.example

benchmark/
  cli.py
  runner.py
  schemas.py
  metrics.py
  reporting.py
  pricing.py
  methods/
    rules_baseline.py
    direct_llm.py
    decomposed_llm.py
    jev_direct.py
    jev_composite.py

cases/
  sec_lines/
    case.yaml
    template.yaml
    prompts.yaml
    rules.yaml
    dataset.py
    template.py
    features.py
    scoring.py

config/
  experiments/
    sec_lines.yaml

tests/
  test_case_contract.py
  test_leakage.py
  test_methods.py
  test_metrics.py
  fixtures/

data/
  raw/
  processed/

results/
```
Case-specific code stays under cases/sec_lines/. Shared code must not import it.
## Interfaces: keep contracts explicit
Define these Pydantic models in benchmark/[schemas.py](http://schemas.py):
```python
class BenchmarkRecord(BaseModel):
    record_id: str
    case_id: str
    source: dict
    input: dict
    reference: str
    groups: dict[str, str]

class MethodResult(BaseModel):
    prediction: str
    confidence: float
    confidence_kind: str
    probability_of_prediction: float | None = None
    diagnostics: dict = {}
```
Every case module must expose:
```python
prepare(case_config) -> Path
load_records(case_config) -> list[BenchmarkRecord]
build_payload(record, context_regime, case_config) -> dict
candidates(record, case_config) -> list[dict]
is_correct(prediction, reference, case_config) -> bool
```
Every method module must expose:
```python
predict(payload, candidates, case_config, method_config) -> MethodResult
```
The runner owns iteration, timing, repeats, retries, result persistence and metric invocation.
# Data: build the line-item case
## Retrieval: download the SEC tables
- Download the FSDS ZIP for every quarter from 2021 Q1 to 2026 Q1, so that fiscal years 2021 to 2025 are covered. Keep the raw ZIPs under data/raw/.
- From sub.txt keep rows where form is 10-K and fp is FY. Retain adsh (filing id), cik, name, sic, fy, period.
- From pre.txt keep rows where stmt is IS or BS. Retain adsh, report, line, stmt, plabel, tag, version, negating.
- From num.txt keep the value for the filing's own fiscal year end: ddate equals period, qtrs is 4 for the income statement and 0 for the balance sheet, coreg is empty. Retain adsh, tag, version, value, uom.
- From tag.txt retain tag, version, tlabel (the standard label), doc, datatype, crdr (debit or credit).
- Join pre.txt to num.txt on adsh, tag and version. Rows with no value are excluded with reason no_value.
## Template: define the answer set
cases/sec_lines/template.yaml lists the 28 template lines and the tags behind each. A tag may appear under one line at most. Tags that combine two template lines, such as AccountsPayableAndAccruedLiabilitiesCurrent, go in an excluded_tags list with a reason.
Starter mapping. The coding agent extends it from the most frequent tags in the data and marks every addition for review.
```yaml
case_id: sec_lines

statements:
  IS: income_statement
  BS: balance_sheet

lines:
  # Income statement
  - id: revenue
    statement: IS
    label: Revenue
    tags: [Revenues, RevenueFromContractWithCustomerExcludingAssessedTax, SalesRevenueNet]
  - id: cost_of_revenue
    statement: IS
    label: Cost of revenue
    tags: [CostOfRevenue, CostOfGoodsAndServicesSold, CostOfGoodsSold]
  - id: gross_profit
    statement: IS
    label: Gross profit
    tags: [GrossProfit]
  - id: research_development
    statement: IS
    label: Research and development
    tags: [ResearchAndDevelopmentExpense]
  - id: sga
    statement: IS
    label: Selling, general and administrative
    tags: [SellingGeneralAndAdministrativeExpense]
  - id: depreciation_amortization
    statement: IS
    label: Depreciation and amortisation
    tags: [DepreciationDepletionAndAmortization, DepreciationAndAmortization]
  - id: other_operating
    statement: IS
    label: Other operating items
    tags: [OtherOperatingIncomeExpenseNet, OtherCostAndExpenseOperating]
  - id: operating_income
    statement: IS
    label: Operating income
    tags: [OperatingIncomeLoss]
  - id: interest_income
    statement: IS
    label: Interest income
    tags: [InvestmentIncomeInterest, InterestIncomeOther]
  - id: interest_expense
    statement: IS
    label: Interest expense
    tags: [InterestExpense]
  - id: other_nonoperating
    statement: IS
    label: Other non-operating income or expense
    tags: [NonoperatingIncomeExpense, OtherNonoperatingIncomeExpense]
  - id: income_tax
    statement: IS
    label: Income tax
    tags: [IncomeTaxExpenseBenefit]
  - id: net_income
    statement: IS
    label: Net income
    tags: [NetIncomeLoss, ProfitLoss]
  # Balance sheet
  - id: cash
    statement: BS
    label: Cash
    tags: [CashAndCashEquivalentsAtCarryingValue, CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents]
  - id: short_term_investments
    statement: BS
    label: Short-term investments
    tags: [ShortTermInvestments, MarketableSecuritiesCurrent]
  - id: receivables
    statement: BS
    label: Receivables
    tags: [AccountsReceivableNetCurrent, ReceivablesNetCurrent]
  - id: inventory
    statement: BS
    label: Inventory
    tags: [InventoryNet]
  - id: other_current_assets
    statement: BS
    label: Other current assets
    tags: [OtherAssetsCurrent, PrepaidExpenseAndOtherAssetsCurrent]
  - id: ppe
    statement: BS
    label: Property, plant and equipment
    tags: [PropertyPlantAndEquipmentNet]
  - id: goodwill_intangibles
    statement: BS
    label: Goodwill and intangibles
    tags: [Goodwill, IntangibleAssetsNetExcludingGoodwill, IntangibleAssetsNetIncludingGoodwill]
  - id: other_noncurrent_assets
    statement: BS
    label: Other non-current assets
    tags: [OtherAssetsNoncurrent]
  - id: accounts_payable
    statement: BS
    label: Accounts payable
    tags: [AccountsPayableCurrent]
  - id: accrued_liabilities
    statement: BS
    label: Accrued liabilities
    tags: [AccruedLiabilitiesCurrent]
  - id: short_term_debt
    statement: BS
    label: Short-term debt
    tags: [DebtCurrent, LongTermDebtCurrent, ShortTermBorrowings]
  - id: other_current_liabilities
    statement: BS
    label: Other current liabilities
    tags: [OtherLiabilitiesCurrent]
  - id: long_term_debt
    statement: BS
    label: Long-term debt
    tags: [LongTermDebtNoncurrent]
  - id: other_noncurrent_liabilities
    statement: BS
    label: Other non-current liabilities
    tags: [OtherLiabilitiesNoncurrent]
  - id: total_equity
    statement: BS
    label: Total equity
    tags: [StockholdersEquity, StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest]

excluded_tags:
  - tag: AccountsPayableAndAccruedLiabilitiesCurrent
    reason: combines accounts payable and accrued liabilities
```
Each template line also carries a one-sentence description in case.yaml, written in plain words, used as the candidate description by every method.
## Records: one row per statement line
Persist complete records separately from model-visible inputs.
```json
{
  "record_id": "stable-sha256-id",
  "case_id": "sec_lines",
  "source": {
    "adsh": "...",
    "cik": "...",
    "name": "...",
    "fy": 2024,
    "sic": "3576",
    "tag": "NonoperatingIncomeExpense",
    "standard_label": "Nonoperating Income (Expense)"
  },
  "input": {
    "label": "Other income, net",
    "statement": "IS",
    "lines_above": ["Total operating expenses", "Income (loss) from operations"],
    "lines_below": ["Income (loss) before income taxes", "Provision for (benefit from) income taxes"],
    "sign": "positive",
    "scale_ratio": 0.019,
    "sic_description": "Computer communications equipment"
  },
  "reference": "other_nonoperating",
  "groups": {
    "template_line": "other_nonoperating",
    "statement": "IS",
    "label_differs": "true",
    "filer_split": "false",
    "baseline_miss": "false",
    "fiscal_year": "2024"
  }
}
```
Rules for the input fields:
- lines_above and lines_below hold the plabel text of the neighbouring rows in presentation order within the same statement, including heading rows. Text only, never tags.
- sign is the sign of the value after applying negating. scale_ratio is the absolute value divided by the filer's revenue (income statement) or total assets (balance sheet) in the same filing; null when the denominator is missing.
- sic_description comes from the SEC SIC code list stored in the repository.
Create record_id as SHA-256 over adsh, report, line.
Deduplicate within a filer: one record per cik, statement and normalised label (lower case, punctuation and whitespace collapsed), keeping the latest fiscal year. Keep identical labels across different filers.
## Eligibility: keep the answer key clean
A row qualifies when:
- stmt is IS or BS;
- plabel is non-empty and is not a heading or abstract row (the row has a value);
- the tag maps to one template line;
- the value for the fiscal year end exists.
Rows that fail are written to excluded_records.parquet with an exclusion_reason.
## Slices: let the data say what is hard
Compute these flags per record before any model run:
- **label_differs**: the normalised plabel differs from the normalised standard label of its tag (tlabel in tag.txt).
- **filer_split**: the normalised label is used by at least five filers and those filers map it to at least two different template lines. Store the observed share of each template line for that label in label_splits.parquet. This is the observed-disagreement distribution used in the calibration analysis.
- **baseline_miss**: the rules baseline answered wrongly or abstained.
## Rules baseline: write code before answers
cases/sec_lines/rules.yaml holds keyword lists per template line and a small set of position rules, for example: a single row between the operating income row and the pre-tax income row is total non-operating income; an "other income" row under a revenue heading is revenue. cases/sec_lines/[features.py](http://features.py) applies them.
The baseline is written from the template definitions and the smoke set, before benchmark answers are inspected, and frozen with the prompts. Where no rule fires, the baseline abstains. An abstention scores as incorrect in accuracy and is reported as coverage.
## Leakage: enforce before inference
Build model payloads from an explicit allowlist of input keys, never by deleting fields from the complete record.
Add a unit test asserting that the set of keys in every serialised payload is a subset of the allowlist, and that no payload value equals the record's tag or standard label.
Log one payload per context regime during the smoke test for manual inspection.
## Reconnaissance: report corpus shape
Before any model call, write data/processed/sec_lines_summary.csv with, per template line: eligible records, unique filers, unique labels, share label_differs, share filer_split.
Also write eligible_records.parquet, excluded_records.parquet, label_splits.parquet, and dataset_manifest.json containing the FSDS quarters used, retrieval timestamp, filters, counts and a hash of the processed dataset.
Sampling happens after eligibility and deduplication:
```plain text
sample_per_line = min(eligible_count_for_line, records_per_line)
```
records_per_line comes from the run profile (see Run profiles). Sample with seed 20261001. A template line with fewer than 50 eligible records is dropped from the full profile and reported. The smoke set is drawn from records outside the benchmark sample.
# Methods: implement comparable decisions
## Contract: return one prediction
All methods return:
```json
{
  "prediction": "other_nonoperating",
  "confidence": 0.87,
  "confidence_kind": "method_specific",
  "diagnostics": {}
}
```
Rules:
- prediction must be a template line id of the record's statement, or ABSTAIN for the rules baseline;
- confidence must be in 0 to 1;
- raw confidence values are not compared across methods;
- confidence_kind states what the number represents;
- all provider usage and raw intermediate outputs go into diagnostics.
## Context regimes: vary information available
Each method runs twice per record:
- **label_only**: label and statement.
- **with_context**: label, statement, lines above and below, sign, scale_ratio, sic_description.
Candidate ids, labels and descriptions are identical across regimes and across methods.
## Prompts: freeze exact wording
Store prompt text in cases/sec_lines/prompts.yaml. Methods load these strings.
```yaml
direct_llm:
  system: >
    Match one line from a company's financial statement to one line of a standard template.
    Use only the supplied record and candidate information.
    Return the single best template line and a confidence from 0 to 1.
    Confidence is your estimate of the probability that the selected line is correct.
    Do not provide rationale.

decomposed_llm:
  system: >
    Score every candidate template line independently on wording fit and position fit.
    Use integer scores from 0 to 4 using the supplied rubric.
    If the information needed for a dimension is missing, use 2 for that dimension.
    Do not choose the final line and do not provide rationale.

jev_direct:
  instructions: >
    Which template line does the statement line described in the state belong to?

jev_composite:
  wording: >
    For candidate {candidate_id}, how well does the statement line's wording mean the same thing as the candidate?
  position: >
    For candidate {candidate_id}, how well does the statement line's place among its neighbouring lines fit the candidate?
    If neighbouring lines are not supplied, choose the middle level.

score_levels:
  - Contradictory or no fit
  - Weak fit
  - Plausible fit or information missing
  - Strong fit
  - Direct fit
```
Serialise the case-generated payload as JSON in the user message. Do not add examples from benchmark records to prompts.
## Metadata fit: compute in code
Sign and scale_ratio are compared with each candidate's expected sign and typical size range (stored in case.yaml) by code, producing a metadata score from 0 to 4 per candidate. The same code feeds both the decomposed LLM and Jev composite. Models score wording and position only.
## Direct LLM: classify once
Initialise the configured model with [langchain.chat](http://langchain.chat)_models.init_chat_model. Use with_structured_output with include_raw=True so the parsed result and provider usage metadata are retained.
Use a Pydantic schema whose category field is a Literal of the candidate ids for the record's statement, plus a confidence float from 0 to 1.
Output mapping: prediction = category, confidence = confidence, confidence_kind = self_reported.
Use temperature 0 where the provider supports it; otherwise omit it and record that in run metadata.
## Decomposed LLM: score fixed dimensions
Two variants, both using the same model as the direct LLM:
- **matrix**: one structured call returns wording and position scores for all candidates of the statement.
- **parallel**: one call per candidate and dimension, sent concurrently, with the same question text as the Jev composite questions.
Combine with equal weights:
```plain text
candidate_score = (wording / 4 + position / 4 + metadata / 4) / 3
```
Select the highest score. Exact ties are recorded as ties: prediction is the first in template order, confidence is 0, and the tie rate is reported.
Set confidence = top score minus second score, confidence_kind = composite_margin.
## Jev direct: use Choice
```python
from typesafe_sdk import Choice, TypeSafeClient
```
Create one Choice whose criteria are the candidate ids of the record's statement with their descriptions.
Set prediction = response.choices\["line"\].choice, confidence = response.choices\["line"\].confidence, confidence_kind = jev_choice_confidence, probability_of_prediction = probabilities\[prediction\]. Store the full probability map.
## Jev composite: use fixed Scores
Ask the wording and position questions for each candidate as TypeSafe Score questions with the five levels above. Use the argmax level as the primary score, so that Jev and the LLM are compared on the same integer scale. Store the expected score (the score field, a decimal) in diagnostics and report it as a secondary variant.
Combine with the same weights, metadata score, tie rule and composite-margin confidence as the decomposed LLM.
Two execution variants:
- **concurrent**: one System One request per question, sent concurrently.
- **fan-out**: all questions for a record in one System One request.
Compare predictions, component scores, tokens, cost and wall-clock latency between the two.
## Failures: retry, then score as wrong
Each model call retries up to three times on transport errors, rate limits or schema violations. After the third failure the record is scored as incorrect for that method and counted in the failure rate.
## Option order: shuffle and compare
Jev's documentation notes that the order of options can change its answer. On the shuffle subset of the run profile, rerun every method with the candidate order shuffled by the run seed and report the share of records whose answer changed, per method.
# Experiment: configure one reproducible run
config/experiments/sec_lines.yaml:
```yaml
case: sec_lines
seed: 20261001
repeat_count: 3
record_concurrency: 1

conventional_llm:
  small:
    provider: ${LLM_SMALL_PROVIDER}
    model: ${LLM_SMALL_MODEL}
  frontier:
    provider: ${LLM_FRONTIER_PROVIDER}
    model: ${LLM_FRONTIER_MODEL}

jev:
  model: ${JEV_MODEL}   # resolved via models.list() at run start and written to the manifest

methods:
  - rules_baseline
  - direct_llm
  - decomposed_llm_matrix
  - decomposed_llm_parallel
  - jev_direct
  - jev_composite_concurrent
  - jev_composite_fanout

context_regimes:
  - label_only
  - with_context

metrics:
  - accuracy
  - accuracy_by_group
  - confidence_coverage
  - calibration
  - split_calibration
  - repeatability
  - failure_rate
  - latency
  - usage
  - cost
```
Store the fully resolved experiment config with every run.
## Run profiles: start small, then go full
Every size in the run is a parameter of a named profile. The small profile proves the mechanism end to end at low cost; the full profile produces the results. Subsets are drawn evenly across template lines with the run seed, and the composite, repeat and shuffle subsets are nested inside the main sample. Every output row carries the profile name.
```yaml
profiles:
  small:
    records_per_line: 20
    composite_records: 200
    repeat_records: 100
    repeat_count: 2
    shuffle_records: 100
  full:
    records_per_line: 300
    composite_records: 1500
    repeat_records: 500
    repeat_count: 3
    shuffle_records: 500
```
- records_per_line: records sampled per template line for the direct methods (rules, direct LLM, Jev direct).
- composite_records: subset on which the decomposed LLM and Jev composite methods run.
- repeat_records and repeat_count: subset and number of repeats for the repeatability measure.
- shuffle_records: subset for the option-order test.
## Pricing: keep costs auditable
Store pricing separately from model logic, with provider, model, input and output cost per million tokens, currency, effective date and source URL. Record raw token usage even when pricing is unavailable. If a model has no configured price, fail before model execution.
# Measurement: compute shared metrics
## Accuracy: score exact predictions
correct = prediction equals reference. Report overall accuracy, accuracy per template line, per statement, per slice (label_differs, filer_split, baseline_miss), per fiscal year, per context regime, and a confusion matrix.
Report the paired bootstrap 95% interval of the accuracy difference between Jev direct and each LLM method, and McNemar's test on the records where the two disagree.
## Confidence: score ranking quality
For every method, sort records by its own confidence. At retained coverage of 100, 90, 80, 70 and 50 percent, report coverage, accuracy and record count. Ties in confidence are broken by record_id.
Compute expected calibration error and Brier score for every method that exposes a probability: Jev direct (probability_of_prediction) and the direct LLM (self-reported confidence, which the prompt defines as a probability). Provider token probabilities are out of scope for this run.
## Split calibration: compare with observed disagreement
For records flagged filer_split, compare each method's probability distribution over template lines (Jev direct: the full probability map; others: the composite scores normalised) with the observed share of filers choosing each line for that label. Report the mean absolute difference per method.
## Repeatability: measure prediction changes
With repeat_count 3, report the share of records with the same prediction in all runs, the share with at least one change, and the mean confidence range across repeats. Use repeat_index 0 for confusion matrices and examples.
## Latency and cost: measure wall time and usage
Report median and 95th percentile record latency, total wall time, total input and output tokens, total cost, cost per record, cost per 1,000 records, and request count per method. For concurrent and fan-out Jev composite, include total method latency per record.
# Results: preserve enough evidence
## Run folder: write immutable outputs
```plain text
results/<run_id>/
  resolved_config.yaml
  dataset_manifest.json
  predictions.parquet
  label_splits.parquet
  metrics.json
  metrics.csv
  dataset_summary.csv
  management_summary.json
  report.md
```
predictions.parquet includes record_id, case_id, context_regime, method, strategy, model, repeat_index, prediction, confidence, confidence_kind, probability_of_prediction, reference, correct, failed, latency_ms, input_tokens, output_tokens, cost_usd, diagnostics_json.
## Management summary: expose deck inputs
management_summary.json contains the case in plain words, dataset counts and years, methods and model versions, accuracy results overall and by slice, the pass-rule outcome with its interval, cost and latency, coverage results, split-calibration results, three highest-confidence correct and incorrect examples per method from repeat_index 0 (ties by record_id), and limitations and exclusions.
# CLI: make execution explicit
```bash
uv sync
uv run python -m benchmark.cli prepare --case sec_lines
uv run python -m benchmark.cli inspect --case sec_lines
uv run python -m benchmark.cli smoke --experiment config/experiments/sec_lines.yaml --records-per-line 5
uv run python -m benchmark.cli run --experiment config/experiments/sec_lines.yaml --profile small
uv run python -m benchmark.cli run --experiment config/experiments/sec_lines.yaml --profile full
uv run python -m benchmark.cli report --run-id <run_id>
```
- prepare downloads the SEC tables, builds records, applies eligibility, computes slices and writes processed data;
- inspect prints counts, exclusions, split labels and five raw examples per template line with references visible;
- smoke runs a small model test on records outside the benchmark sample and writes payload examples;
- run executes the frozen benchmark;
- report regenerates metrics and reports from stored record-level results only.
# Acceptance: remove implementation ambiguity
The build is complete when all of the following pass:
1. prepare builds the dataset from the public SEC tables on a clean machine.
2. Every eligible record has exactly one template line as reference, and every tag in template.yaml appears under one line.
3. Model-visible payloads are generated from an allowlist and contain no tag or standard label.
4. The same record ids are supplied to every method for a given context regime.
5. All conventional methods use the configured small and frontier models; both tiers run.
6. Decomposed LLM and Jev composite use the same dimensions, rubric, code-computed metadata score, weights, tie rule and confidence formula.
7. Jev concurrent and fan-out composite use identical questions and scoring.
8. The rules baseline is frozen before benchmark answers are inspected and runs on every record.
9. All methods produce the common prediction contract, and failures are recorded, not dropped.
10. Metrics regenerate from predictions.parquet without model calls.
11. A fixture case under tests/fixtures/ runs through the runner without importing sec_lines code.
12. Unit and integration tests pass with uv run pytest.
13. [README.md](http://README.md) contains setup, credentials, commands, source links and expected output locations.
## Environment: require explicit credentials
```plain text
TYPESAFE_API_KEY=
JEV_MODEL=jev-latest
LLM_SMALL_PROVIDER=
LLM_SMALL_MODEL=
LLM_FRONTIER_PROVIDER=
LLM_FRONTIER_MODEL=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
SEC_USER_AGENT=
```
Never commit API keys, downloaded data sets, or results containing credentials.
## Handoff: stop before interpretation
The coding agent's task ends when the benchmark runs, tests pass and result artefacts are produced. It must not change the template after seeing results, tune prompts, rules or weights against benchmark answers, select a preferred method, or write the management conclusion.
# Later cases: one addition needed
Cases 2 and 3 (entity matching, loan type) need a yes or no output type in the method contract. Add it when case 2 is specified.

