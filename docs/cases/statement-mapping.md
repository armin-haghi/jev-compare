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

A line is in scope when its filed tag is on the template's tag list. Other lines are excluded before sampling.

| Step | Lines | Share of all lines |
| --- | --- | --- |
| Income-statement and balance-sheet lines in the selected filings | 1,694,559 | 100% |
| Tag on the template list, standard taxonomy, one consolidated USD value | 412,512 | 24.3% |
| After removing repeats of the same wording by the same company | 148,422 | 8.8% |
| Sampled for the 2026-10-02 run: 100 per category | 2,900 | 0.2% |

Lines left out, grouped approximately by tag name:

| Group | Share of all lines | Examples |
| --- | --- | --- |
| Line items whose tag is not on the list | 29% | General and administrative; sales and marketing; lease liabilities; deferred revenue; deferred tax; prepaid expenses |
| Per-share figures and share counts | 17% | Earnings per share; weighted-average shares; par value |
| Totals and subtotals that are not template categories | 12% | Total assets; total operating expenses; income before tax |
| Equity components | 9% | Retained earnings; additional paid-in capital; treasury stock |
| Company-specific tags | 6% | A company's own tag where no standard tag fitted |
| Other | 3% | "Commitments and contingencies"; combined lines such as "Accounts payable and accrued liabilities"; lines without one consolidated value |

Example: 8 of the 22 lines on Samsara's FY2024 income statement are in scope.

| Line as filed | In scope |
| --- | --- |
| Revenue; Cost of revenue; Gross profit; Research and development | Yes |
| Sales and marketing; General and administrative | No: tag not on the list |
| Lease modification, impairment, and related charges | No: company-specific tag |
| Legal settlement | No: tag not on the list |
| Total operating expenses | No: subtotal |
| Loss from operations; Interest income and other income, net | Yes |
| Loss before provision for income taxes | No: subtotal |
| Provision for income taxes; Net loss | Yes |
| Four comprehensive-income lines; four per-share and share-count lines | No |

What the scope means for results:

- Each category contains only lines that carry that category's own tags, and their wording usually names the category. In-scope SG&A lines read "Selling, general and administrative"; lines such as Samsara's "General and administrative" are not tested.
- In the 2026-10-02 run, keyword rules mapped 70% of sampled records correctly. 22 of 29 categories scored 97% or higher for both models. Four "other" and "total" categories account for 89 of Jev's 123 incorrect answers and 97 of GPT-5 mini's 138.
- Results describe in-scope lines only: about a third of a typical income statement and a fifth of a typical balance sheet. The comparison between methods is valid within that scope.

## Patterns tested

| Pattern | In this case |
| --- | --- |
| Confidence-gated routing | Confidence cut-offs and calibration for both models. Jev's answers below a cut-off are compared with GPT-5 mini's answers on the same records. |
| Speculative fan-out | Next run: one call asks for the category and whether the line is a total or subtotal, compared with two separate calls, for both models. |
| Composite scoring | Not tested: the case chooses one category rather than ranking candidates. |
| Intent routing | Not tested: the case has one request type. |

## Decided for the next run

- Sample at random from the in-scope lines, without a quota per category. The 2026-10-02 run took 100 records per category, which gave rare categories more weight than they have in filings.
- Run the consistency checks on a random tenth of the sample each: about 290 records asked twice and about 290 with reordered options. The 2026-10-02 run used 20 records for each check.
- Test speculative fan-out as described under patterns tested.
- Add a "not mapped" answer for totals, subtotals and per-share lines that are not template categories. The tags answered "not mapped" are listed before inference. Recognising lines that should not be mapped becomes part of the task. With random sampling, that list also sets the share of "not mapped" lines in the sample: totals, subtotals and per-share lines together outnumber the current in-scope lines.
- Remove repeats across years only. Repeated wording within one filing stays in, for example several lines worded "Other" in different balance-sheet sections. The 2026-10-02 dataset dropped 5,964 such lines.

## To revisit if the comparison is inconclusive

- Widen the tag list with lines a template would absorb into an existing category: general and administrative and sales and marketing into SG&A, lease liabilities into other liabilities, equity components into total equity, the plain "Cash" tag into cash. Several of these are judgement calls; the mapping would be fixed and recorded before inference.
- Company-specific tags stay out: they have no automatic answer key.
