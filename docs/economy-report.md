# The sample contains 2,900 records

This test maps company financial-statement labels to 29 standard categories using filed accounting tags as the answer key. It compares Jev and GPT-5 mini on United States Securities and Exchange Commission (SEC) filings, with fixed matching rules as a baseline.

| Property | Tested sample |
| --- | --- |
| Records | 2,900 observed of 2,900 selected; 148,422 eligible in the source corpus |
| Categories | 29; 100 records per category |
| Companies | 2,304 distinct filers |
| Fiscal years | 2021, 2022, 2023, 2024, 2025 |
| Statements | Balance sheet: 1,500; Income statement: 1,400 |
| Label properties | 1,093 have wording mapped differently across filers; 2,558 differ from the standard label |
| Subsets | Composite: 100; repeat: 20; option shuffle: 20 |
| Filing archives | 2021q1–2026q1 |

Sampling balances answer categories; aggregate accuracy does not estimate the natural filing mix.
Source: [validation snapshot](economy-validation.json), including dataset provenance, selected record IDs and raw-evidence hashes.

- Filed tags are a proxy answer key, not independently audited truth.
- The 2026 Q1 cutoff excludes later filings for fiscal year 2025.
- Eligibility requires standard mapped tags and consolidated values denominated in United States dollars.
- Available SEC presentation rows may omit headings.

## Jev cuts direct costs 77%

Direct with context (2,900 records): Jev 95.76% vs openai/gpt-5-mini 95.24%; cost 76.9% lower (4.3× cheaper) at list prices. The observed direct comparison favors Jev on accuracy and cost.

Accuracy difference: +0.52 percentage points; 95% interval -0.14 to +1.20, resampling companies. An accuracy advantage is not established. Review direct-method errors on the intended workload; assess composite scoring separately.

Source: [computed metrics](economy-validation.json).

Run: 20261002T232137Z-571ebdd4. Mode: benchmark. Complete: True.
Known list-price cost: $4.1840; provider requests: 28,568.
Direct methods choose a category. Composite methods combine wording, position and numeric-metadata scores; matrix and bundled variants request all scores together, while separate-question variants use individual calls. Failed calls and abstentions count as wrong; composite and direct sample sizes differ.

| Method | Context | Records | Accuracy | Failures | Cost per 1,000 |
| --- | --- | ---: | ---: | ---: | ---: |
| GPT-5 mini matrix | label_only | 100 | 34.00% | 0.00% | $ 0.7779 |
| GPT-5 mini matrix | with_context | 100 | 64.00% | 0.00% | $ 0.8190 |
| GPT-5 mini separate questions | label_only | 100 | 11.00% | 0.00% | $ 6.2257 |
| GPT-5 mini separate questions | with_context | 100 | 9.00% | 0.00% | $ 6.7496 |
| GPT-5 mini direct | label_only | 2900 | 94.24% | 0.00% | $ 0.2333 |
| GPT-5 mini direct | with_context | 2900 | 95.24% | 0.00% | $ 0.2510 |
| Jev separate questions | label_only | 100 | 93.00% | 0.00% | $ 1.1949 |
| Jev separate questions | with_context | 100 | 95.00% | 0.00% | $ 1.3156 |
| Jev bundled questions | label_only | 100 | 93.00% | 0.00% | $ 0.1427 |
| Jev bundled questions | with_context | 100 | 94.00% | 0.00% | $ 0.1469 |
| Jev direct | label_only | 2900 | 94.21% | 0.00% | $ 0.0539 |
| Jev direct | with_context | 2900 | 95.76% | 0.00% | $ 0.0580 |
| Rules | label_only | 2900 | 69.79% | 0.00% | $ 0.0000 |
| Rules | with_context | 2900 | 69.79% | 0.00% | $ 0.0000 |

## GPT-5 mini dominates spending

| Model | Requests | Input tokens | Output tokens | List-price cost |
| --- | ---: | ---: | ---: | ---: |
| openai/gpt-5-mini | 14,284 | 9,791,643 | 507,534 | $3.4630 |
| typesafe-ai/jev | 14,284 | 17,166,474 | 1,254,165 | $0.7210 |

This run cost $4.1840. All five recorded runs total $5.6677 in known list-price usage. The interrupted prerequisite contains 40 requests with unknown usage; its additional $0.3788 reservation is not a measured charge. See the [cost ledger](economy-validation.json).

## The brief sets acceptance targets

The original criterion requires an accuracy loss no greater than 2 percentage points at the lower end of a 95% interval, plus either cost at most one-fifth of the comparator or higher accuracy among the most confident 80% of answers.

Source: [brief as imported before implementation](https://github.com/armin-haghi/jev-compare/blob/e05b745/docs/build-brief.md#L39). The snapshot does not identify who originally selected the cutoffs.

The implementation applies the criterion to records shared by Jev direct and all conventional-model methods, and resamples companies to account for correlated records.

These are project acceptance targets. Practical value is assessed separately from measured accuracy, cost and uncertainty.

| Context | Shared records | Accuracy-difference interval | Cost relative to comparator | Higher accuracy at 80% coverage | Original criterion |
| --- | ---: | --- | --- | --- | --- |
| label only | 100 | -6.06 to +2.00 points | 23.1% (target ≤20%) | Yes | Unmet |
| with context | 100 | -3.00 to +3.00 points | 23.1% (target ≤20%) | Yes | Unmet |

The shared-sample interval extends below the allowed 2-point loss. That explains the unmet original criterion; the full direct comparison above uses its own larger sample and interval.

Where retained-answer accuracy is higher, that satisfies the alternative benefit test; the 5× cost target is not required. Each method retains its own most confident 80%, so accepted records can differ.

## Confidence ranks retained answers

![Coverage and error rate for label_only](economy-coverage-label_only.svg)

![Coverage and error rate for with_context](economy-coverage-with_context.svg)

## Limits bound these measurements

- Filed tags are a proxy answer key, not independently audited truth.
- The 2026 Q1 cutoff excludes later filings for fiscal year 2025.
- Eligibility requires standard mapped tags and consolidated values denominated in United States dollars.
- Available SEC presentation rows may omit headings.
- Costs use uncached list prices; billed invoice costs may differ.
- Composite scores are not correctness probabilities.
- Record concurrency: 4; question concurrency: 2. Latency is measured under this load.

The [validation snapshot](economy-validation.json) includes configuration, dataset provenance, source hashes, matched comparisons, calibration, repeatability and option-order results. Raw artifacts are retained locally under results/20261002T232137Z-571ebdd4/.
