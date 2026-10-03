# Jev cuts direct costs 77%

**Recommendation:** Start with Jev, TypeSafe’s fixed-choice decision model, for financial-statement mapping. Ask for the final category in one call. It cost less without reducing observed overall accuracy.

**Total run cost: $4.1840** (GPT-5 mini $3.4630; Jev $0.7210). Uncached list-price estimate in US dollars, covering all variants and checks; not an invoice.

## The test covers 2,900 mappings

The test compares Jev with GPT-5 mini and programmed rules on accuracy, cost, speed and confidence for routing uncertain mappings to review.

| Dataset property | Tested value |
| --- | --- |
| Sample | 2,900 observed records; 29 categories, 100 each |
| Companies and period | 2,304 filers; fiscal years 2021, 2022, 2023, 2024, 2025 |
| Statement mix | 1,500 balance-sheet lines; 1,400 income-statement lines |
| Ambiguous wording | 1,093 records have wording mapped differently across companies |
| Additional checks | 100 records for extra scoring; 20 repeated; 20 with reordered options |

Source: public United States Securities and Exchange Commission filings. Filed tags supply the answer key and are hidden from model input. Category balancing differs from a production workload.

## Accuracy differences remain uncertain

Each model chose one category from the same options, with nearby lines and financial context.

| Model | Correct / tested | Accuracy | Cost / 1,000 | Median response |
| --- | --- | --- | --- | --- |
| Jev | 2,777/2,900 | 95.76% | $0.0580 | 0.627s |
| GPT-5 mini | 2,762/2,900 | 95.24% | $0.2510 | 1.296s |

Accuracy difference: +0.52 percentage points; 95% interval -0.14 to +1.20, resampling companies. An accuracy advantage is not established.

**Rules:** 2,035/2,900 answered at 99.46% accuracy; 865 unresolved. Model-service cost: $0.

**Review tradeoff:** retaining each model’s most confident 80% (2,320 answers) leaves GPT-5 mini: 49 errors; Jev: 15 errors. Each defers 580 records; selected records differ. Human-review results remain unmeasured.

## Identical labels produce different outcomes

Illustrations: one Jev success, one comparator success and one shared failure where available, selected for ambiguous, short labels. Excerpts show the nearest lines around the **target**; examples do not represent outcome frequencies.

| Statement excerpt | Filed-tag answer | Jev answer | GPT-5 mini answer |
| --- | --- | --- | --- |
| CNL STRATEGIC RESIDENTIAL CREDIT, INC., 2025: Total revenues → **Other** → Total operating expenses | Other operating income/expense | Other operating income/expense | Other non-operating income/expense |
| MANAGED FUTURES PREMIER WARRINGTON L.P., 2022: Professional fees → **Other** → Total expenses | Other operating income/expense | Selling, general and administrative expenses | Other operating income/expense |
| IRONWOOD PHARMACEUTICALS INC, 2025: Interest and investment income → **Other** → Other income (expense), net | Other non-operating income/expense | Total non-operating income/expense | Total non-operating income/expense |

## Extra scoring added cost

On the same 100 records, we tested whether scoring each candidate’s wording and context separately helped. Code combined the scores to choose a category.

| Model | Task | Calls / record | Correct / tested | Cost / 1,000 |
| --- | --- | --- | --- | --- |
| Jev | Choose a category | 1 | 98/100 | $0.0581 |
| Jev | Score all categories in one call | 1 | 94/100 | $0.1469 |
| Jev | Score each category in separate calls | 28–30 | 95/100 | $1.3156 |
| GPT-5 mini | Choose a category | 1 | 98/100 | $0.2514 |
| GPT-5 mini | Score all categories in one call | 1 | 64/100 | $0.8190 |
| GPT-5 mini | Score each category in separate calls | 28–30 | 9/100 | $6.7496 |

The extra scoring brought no accuracy gain for Jev and added cost. Ask for the final category in one call.

GPT-5 mini gave tied top scores on 84/100 records in separate calls; fixed category order broke those ties. This configuration performed poorly.

**Counterevidence:** for other non-operating income/expense, Jev matched 74/100 tags versus GPT-5 mini's 88/100.

Filed tags are a proxy for accounting correctness. Other finance tasks, models, integration costs and review costs remain unmeasured.

Run `20261002T232137Z-571ebdd4`: 18,760 outputs, 28,568 requests, 0 failed outputs, 0 outputs with unknown usage.

Sources: [run evidence](evidence.json) includes metrics, example inputs and filed tags, configuration, historical criteria and source hashes. [Shared methodology](../../docs/methodology.md) defines the comparisons; its preserved run version is embedded in the evidence.
