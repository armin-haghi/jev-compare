# Statement mapping case

Case ID: `sec_lines`. Code and frozen configuration: [cases/sec_lines/](../../cases/sec_lines/). Shared definitions: [methodology](../methodology.md).

## Decision

Given one line from a company's income statement or balance sheet, choose its category from a fixed template of 29 categories: 14 for the income statement and 15 for the balance sheet. Each record is offered only the categories for its own statement. [Template](../../cases/sec_lines/template.yaml).

## Source and answer key

- Source: SEC Financial Statement Data Sets, quarterly archives 2021q1–2026q1. Annual reports (10-K) for fiscal years 2021–2025; consolidated US-dollar values only.
- Answer key: the line's filed us-gaap tag, converted to a category through the template's tag list (46 tags). The tag and its standard label are withheld from model input.
- An answer is correct when it matches the category of the filed tag. The tag records the company's own judgement; it is not independently reviewed.

## Model input

- Label only: the line's wording and statement type.
- With context: adds up to two neighbouring lines on each side, the sign of the amount, its size relative to revenue (income statement) or total assets (balance sheet), and the company's industry description.

Example: "Other income, net" can be the non-operating total or one component of it. The neighbouring lines usually show which.

## Test scope

The scope is deliberately limited. The study compares methods on a defined set of lines; it does not measure how well a method maps a complete statement.

A line is in scope when its filed tag is on the template's tag list, or on the list of totals and subtotals the template does not hold. Those totals and subtotals (for example total assets, total operating expenses and income before tax) are answered "not mapped", so recognising lines that should not be mapped is part of the task. Every record is offered its statement's categories plus "not mapped". Other lines are excluded before sampling.

When a company uses the same wording in several annual reports, only its latest report's lines are kept. Lines that repeat a wording within one report, such as several lines worded "Other" in different balance-sheet sections, all stay, because their position gives them different meanings.

| Step | Lines | Share of all lines |
| --- | --- | --- |
| Income-statement and balance-sheet lines in the selected filings | 1,694,559 | 100% |
| Tag on the template list or the not-mapped list, standard taxonomy, one consolidated USD value | 597,580 | 35.3% |
| After keeping each company's latest report for a wording | 210,738 | 12.4% |
| Dataset `sec_lines-2900-8bad7b33`: random sample | 2,900 | 0.2% |

In the dataset, 819 of the 2,900 lines (28%) are totals and subtotals answered "not mapped".

Lines left out, grouped approximately by tag name:

| Group | Share of all lines | Examples |
| --- | --- | --- |
| Line items whose tag is not on the list | 28.5% | General and administrative; sales and marketing; lease liabilities; deferred revenue; deferred tax; prepaid expenses |
| Per-share figures and share counts | 17.2% | Earnings per share; weighted-average shares; par value |
| Equity components | 9.0% | Retained earnings; additional paid-in capital; treasury stock |
| Company-specific tags | 6.1% | A company's own tag where no standard tag fitted |
| Other totals, comprehensive-income items and placeholders | 2.9% | Net interest income; "Commitments and contingencies" |
| Combined lines and lines without one consolidated value | 1.1% | "Accounts payable and accrued liabilities" |

Example: 12 of the 22 lines on Samsara's FY2024 income statement are in scope.

| Line as filed | In scope |
| --- | --- |
| Revenue; Cost of revenue; Gross profit; Research and development | Yes |
| Sales and marketing; General and administrative | No: tag not on the list |
| Lease modification, impairment, and related charges | No: company-specific tag |
| Legal settlement | No: tag not on the list |
| Total operating expenses | Yes, answered "not mapped" |
| Loss from operations; Interest income and other income, net | Yes |
| Loss before provision for income taxes | Yes, answered "not mapped" |
| Provision for income taxes; Net loss | Yes |
| Other comprehensive income (loss); Comprehensive loss | Yes, answered "not mapped" |
| Two comprehensive-income components; four per-share and share-count lines | No |

What the scope means for results:

- Each category contains only lines that carry that category's own tags, and their wording usually names the category. In-scope SG&A lines read "Selling, general and administrative"; lines such as Samsara's "General and administrative" are not tested.
- In the 2026-10-02 run, which had no "not mapped" answer, keyword rules mapped 70% of sampled records correctly. 22 of 29 categories scored 97% or higher for both models. Four "other" and "total" categories account for 89 of Jev's 123 incorrect answers and 97 of GPT-5 mini's 138.
- Results describe in-scope lines only. The comparison between methods is valid within that scope.

## Patterns tested

| Pattern | In this case |
| --- | --- |
| Confidence-gated routing | Confidence cut-offs and calibration for both models. Jev's answers below a cut-off are compared with GPT-5 mini's answers on the same records. |
| Speculative fan-out | Planned as a separate run on the same dataset: one call asks for the category and whether the line is a total or subtotal, compared with two separate calls. |
| Composite scoring | Not tested: the case chooses one category rather than ranking candidates. |
| Intent routing | Not tested: the case has one request type. |

## To revisit if the comparison is inconclusive

- Widen the tag list with lines a template would absorb into an existing category: general and administrative and sales and marketing into SG&A, lease liabilities into other liabilities, equity components into total equity, the plain "Cash" tag into cash. Several of these are judgement calls; the mapping would be fixed and recorded before inference.
- Company-specific tags stay out: they have no automatic answer key.
