# The sample contains 2,900 records

This run maps company financial-statement labels using public United States Securities and Exchange Commission (SEC) filings and company-filed tags as the answer key. Tested models: GPT-5 mini, Jev. See the [methodology](economy-methodology.md) for workflow definitions and scoring.

| Property | Tested sample |
| --- | --- |
| Records | 2,900 observed of 2,900 selected; 148,422 eligible in the source corpus |
| Categories | 29; 100 records per category |
| Companies | 2,304 distinct filers |
| Fiscal years | 2021, 2022, 2023, 2024, 2025 |
| Statements | Balance sheet: 1,500; Income statement: 1,400 |
| Label properties | 1,093 have wording mapped differently across filers; 2,558 differ from the standard label |
| Subsets | Multi-question comparison: 100; repeat checks: 20; answer-order checks: 20 |
| Filing archives | 2021q1–2026q1 |

Sampling balances answer categories; aggregate accuracy does not estimate the natural filing mix.
Source: [dataset manifest](economy-validation.json), [selected record IDs](economy-validation.json).


## Jev cuts direct costs 77%

Direct with context (2,900 records): Jev 95.76% vs GPT-5 mini 95.24%; cost 76.9% lower (4.3× cheaper) at list prices. The observed direct comparison favors Jev on accuracy and cost.

Accuracy difference: +0.52 percentage points; 95% interval -0.14 to +1.20, resampling companies. An accuracy advantage is not established.

The table uses surrounding context.

| Workflow | Correct / records | Accuracy | Abstentions | Cost / 1,000 | Median / 95th-percentile time |
| --- | --- | --- | --- | --- | --- |
| GPT-5 mini: choose a category | 2,762 / 2,900 | 95.24% | 0 | $0.2510 | 1.296s / 1.773s |
| Jev: choose a category | 2,777 / 2,900 | 95.76% | 0 | $0.0580 | 0.627s / 0.911s |
| Programmed rules | 2,024 / 2,900 | 69.79% | 865 | $0.0000 | 0.083ms / 0.201ms |

Rules answered 2,035/2,900 records (70.17%); 99.46% of those answers matched the key. Their 865 abstentions are unresolved work, not incorrect emitted labels. Model-service cost is zero; implementation and maintenance costs are not measured.

The direct-call cost difference is $0.1930 per 1,000 records in Jev’s favor. These are uncached list-price estimates from measured tokens. Human review, integration and the cost of errors are not included.

| Workflow | Matched records | Labels without context | With context |
| --- | --- | --- | --- |
| GPT-5 mini: choose a category | 2,900 | 94.24% | 95.24% |
| Jev: choose a category | 2,900 | 94.21% | 95.76% |
| Programmed rules | 2,900 | 69.79% | 69.79% |

| Difficult subset | Workflow | Correct / records | Accuracy |
| --- | --- | --- | --- |
| Rules were wrong or abstained | GPT-5 mini: choose a category | 748 / 876 | 85.39% |
| Same wording maps differently across companies | GPT-5 mini: choose a category | 993 / 1,093 | 90.85% |
| Rules were wrong or abstained | Jev: choose a category | 755 / 876 | 86.19% |
| Same wording maps differently across companies | Jev: choose a category | 1,009 / 1,093 | 92.31% |

Aggregate accuracy hides category differences. These are the three lowest-accuracy categories for Jev direct, selected after scoring as a descriptive error review.

| Category | Workflow | Correct / records | Accuracy |
| --- | --- | --- | --- |
| other current liabilities | GPT-5 mini: choose a category | 88 / 100 | 88.00% |
| other current liabilities | Jev: choose a category | 92 / 100 | 92.00% |
| other nonoperating | GPT-5 mini: choose a category | 88 / 100 | 88.00% |
| other nonoperating | Jev: choose a category | 74 / 100 | 74.00% |
| other operating | GPT-5 mini: choose a category | 58 / 100 | 58.00% |
| other operating | Jev: choose a category | 52 / 100 | 52.00% |

Source: [saved analysis](economy-validation.json), [computed metrics](economy-validation.json).

## Jev confidence leaves fewer errors

The table retains each method’s most confident 80% in this run.

| Workflow | Retained | Deferred | Errors retained | Retained accuracy |
| --- | --- | --- | --- | --- |
| GPT-5 mini: choose a category | 2,320 | 580 | 49 | 97.89% |
| Jev: choose a category | 2,320 | 580 | 15 | 99.35% |

At the same retained volume, Jev’s confidence ranking leaves fewer incorrect mappings in the accepted work. This supports using confidence to identify records needing review.

Source: [saved analysis](economy-validation.json), [computed metrics](economy-validation.json).

## Jev direct leads its combinations

Every row below uses the same shared records in this run.

| Model | What we asked it to do | Calls / record | Correct / shared records | Cost / 1,000 | Tied top scores |
| --- | --- | --- | --- | --- | --- |
| GPT-5 mini | Choose a category | 1 | 98 / 100 | $0.2514 | 0 / 100 |
| GPT-5 mini | Score all categories in one call | 1 | 64 / 100 | $0.8190 | 30 / 100 |
| GPT-5 mini | Score each category in separate calls | 28–30 | 9 / 100 | $6.7496 | 84 / 100 |
| Jev | Choose a category | 1 | 98 / 100 | $0.0581 | 0 / 100 |
| Jev | Score all categories in one call | 1 | 94 / 100 | $0.1469 | 5 / 100 |
| Jev | Score each category in separate calls | 28–30 | 95 / 100 | $1.3156 | 5 / 100 |
| rules-v1 | Match programmed rules | 0 | 78 / 100 | $0.0000 | 0 / 100 |

The extra scoring brought no accuracy gain for Jev and added cost. Ask for the final category in one call.

| Workflow | Changed on repeat / checked | Changed after reordering / checked |
| --- | --- | --- |
| GPT-5 mini: score all categories in one call | 4 / 20 | 6 / 20 |
| GPT-5 mini: score each category in separate calls | 6 / 20 | 16 / 20 |
| GPT-5 mini: choose a category | 0 / 20 | 0 / 20 |
| Jev: score each category in separate calls | 0 / 20 | 1 / 20 |
| Jev: score all categories in one call | 3 / 20 | 0 / 20 |
| Jev: choose a category | 0 / 20 | 0 / 20 |
| Programmed rules | 0 / 20 | 0 / 20 |

Source: [saved analysis](economy-validation.json), [computed metrics](economy-validation.json).

## The evidence favors Jev direct

Prefer asking Jev for the final category in one call. It cost less than GPT-5 mini without reducing observed overall accuracy on this task. The acceptable error rate depends on the business.

Jev direct disagreed with the key on 123/2,900 records in the primary condition. The error categories and retained-error counts above should determine where review remains necessary; this study assigns no monetary value to a wrong mapping.

Programmed rules remain useful where their answered subset fits the required coverage. Routing rules’ unresolved records to a model is a plausible implementation option, but that combined workflow was not tested.

The conventional direct model remains an alternative, with its observed strengths and weaknesses shown by category. The tested combined-score workflows should be judged against direct calls, including their extra cost and instability, rather than treated as an inherent benefit of Jev’s approach.

The conclusion applies to this sampled task and these configurations. It does not establish performance on other finance data-management tasks or untested models. The balanced category mix differs from a natural production workload, and the answer key is not an independent review of accounting correctness.

Source: [saved analysis](economy-validation.json), [computed metrics](economy-validation.json).

## Saved evidence supports these findings

Run 20261002T232137Z-571ebdd4: 18,760 saved outputs, 28,568 provider requests, 0 failed outputs and 0 outputs with unknown usage. Total known list-price cost: $4.1840. All costs are in United States dollars. This total includes every input condition, workflow and repeat/order check; it is not the cost of one direct pass.

| Model | Requests | Input tokens | Output tokens | Known list-price cost |
| --- | --- | --- | --- | --- |
| GPT-5 mini | 14,284 | 9,791,643 | 507,534 | $3.4630 |
| Jev | 14,284 | 17,166,474 | 1,254,165 | $0.7210 |

Execution used 4 concurrent records and up to 2 concurrent score questions per record. The saved model identifiers and prices describe the run; provider aliases need not identify immutable model weights.

Evidence: [analysis](economy-validation.json), [metrics](economy-validation.json), [dataset manifest](economy-validation.json), [selected record IDs](economy-validation.json), [configuration](economy-validation.json), [prompts](economy-validation.json). Raw predictions are retained beside the local report; the shareable evidence snapshot includes their hash.

The [historical criterion audit](economy-criterion-audit.md) preserves the original brief’s numerical targets and outcomes. It does not determine this report’s recommendation. The recommendation follows the measured task-level tradeoffs above.

![Share of answers retained versus their error rate, label only](economy-coverage-label_only.svg)

![Share of answers retained versus their error rate, with context](economy-coverage-with_context.svg)

- Filed tags are a proxy answer key, not independently audited truth.
- The 2026 Q1 cutoff excludes later filings for fiscal year 2025.
- Only standard mapped tags and consolidated USD values qualify.
- Available SEC presentation rows may omit headings.
- Costs use uncached list prices; billed invoice costs may differ.
- Composite scores are not correctness probabilities.
- Record concurrency: 4; question concurrency: 2. Latency is measured under this load.
