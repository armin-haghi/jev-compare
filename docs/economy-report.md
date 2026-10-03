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

| Workflow | Labels alone | With context | Cost / 1,000 | Median response |
| --- | --- | --- | --- | --- |
| GPT-5 mini direct | 94.24% (2,733/2,900) | 95.24% (2,762/2,900) | $0.2510 | 1.296s |
| Jev direct | 94.21% (2,732/2,900) | 95.76% (2,777/2,900) | $0.0580 | 0.627s |
| Programmed rules | 69.79% (2,024/2,900) | 69.79% (2,024/2,900) | $0.0000 | 0.083ms |

Cost and timing use with context; costs are estimated United States dollars.

Rules answered 2,035/2,900 records at 99.46% accuracy among answers, leaving 865 unresolved.

Keeping each method’s most confident 80% retains 2,320 records and defers 580: GPT-5 mini direct leaves 49 errors (97.89% accuracy); Jev direct leaves 15 errors (99.35% accuracy). Each method selects different records; human-review outcomes were not measured.

The combined-workflow comparison uses the same 100 records for every method:

| Workflow | Correct / records | Cost / 1,000 |
| --- | --- | --- |
| GPT-5 mini combined, bundled | 64 / 100 | $0.8190 |
| GPT-5 mini combined, separate | 9 / 100 | $6.7496 |
| GPT-5 mini direct | 98 / 100 | $0.2514 |
| Jev combined, separate | 95 / 100 | $1.3156 |
| Jev combined, bundled | 94 / 100 | $0.1469 |
| Jev direct | 98 / 100 | $0.0581 |

The tested Jev combinations add cost without improving accuracy over Jev direct on the same records. Prefer the direct workflow for this task on this evidence.

Direct decisions did not change in the repeat/order checks: GPT-5 mini direct checked 20 repeated and 20 reordered records; Jev direct checked 20 repeated and 20 reordered records. These small checks do not establish universal stability.

## The evidence favors Jev direct

Prefer Jev direct for this tested task: it costs less than the direct language-model comparator without an observed aggregate accuracy loss. This is a recommendation about the measured tradeoff; the acceptable error rate depends on the business.

The aggregate hides weaknesses: for “other nonoperating”, Jev scored 74/100 versus GPT-5 mini direct's 88/100. This is a descriptive category check, not proof of a general advantage.

This supports a choice for this task and these configurations. Public filed tags are a proxy answer key; the category-balanced sample does not represent every production workload. Other finance tasks, untested models, integration costs and review costs remain unmeasured.

Run 20261002T232137Z-571ebdd4: 18,760 outputs across all variants and checks, 28,568 requests, 0 failed outputs; $4.1840 known list-price cost. Unknown-usage outputs: 0.

Sources: [methodology](economy-methodology.md), [detailed analysis](economy-details.md), [results and uncertainty](economy-validation.json), [recommendation evidence](economy-validation.json), [configuration](economy-validation.json). The [historical criterion](economy-criterion-audit.md) is retained for audit; it does not decide the recommendation.
