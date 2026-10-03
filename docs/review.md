# The brief supports a bounded comparison

This benchmark measures agreement with company-filed tags on eligible financial statement rows. Jev is TypeSafe's fixed-choice decision model; conventional large language models provide the comparison. Results describe this filtered public corpus, rather than all finance decisions or independently verified accounting truth.

## The template separates totals

The original 28-line template merges the two non-operating categories used in the parent page's motivating example. The implementation uses 29 lines: NonoperatingIncomeExpense maps to total_nonoperating; OtherNonoperatingIncomeExpense maps to other_nonoperating. The original parent page and brief remain preserved. Tag additions require review before freezing; no mapping is expanded automatically after results.

## Data selection needs safeguards

| Finding | Implementation |
| --- | --- |
| Numeric tables contain dimensions and multiple units | Require consolidated, non-segmented USD values; exclude conflicting values explicitly. |
| Custom tags can reuse standard names | Require a standard us-gaap taxonomy version and a non-custom tag definition. |
| The quarter cutoff omits late FY2025 filings | Report the 2026 Q1 retrieval cutoff as a coverage limitation. |
| Financial Statement Data Sets omit some presentation context | Preserve available presentation rows; do not manufacture missing headings. |
| Printed labels often equal standard labels | Permit natural label equality; prevent provenance fields and taxonomy identifiers from being injected. A blanket value-equality ban would exclude valid source text. |
| Filers contribute multiple correlated rows | Report paired row bootstrap and filer-cluster bootstrap intervals; use the latter for the pass rule. |

## Comparisons need matched records

Direct methods run on the main sample; composite methods run on a nested subset. Each pairwise comparison uses the records shared by that pair: the economy run's direct comparison uses 2,900 records. The best-language-model pass rule uses the intersection across Jev direct and all conventional-model methods, which reduces its economy sample to 100 records. Results remain separate by context regime. The best comparator is selected by accuracy, then method name; this exploratory selection is disclosed rather than represented as a confirmatory statistical claim.

Smoke records are reserved outside the full-profile sample, so smoke answers cannot later enter either benchmark profile. Small samples are nested in full samples; repeat and shuffle samples for composite methods are drawn from their evaluated intersection.

## The brief supplied the cutoffs

The [brief imported before implementation](https://github.com/armin-haghi/jev-compare/blob/e05b745/docs/build-brief.md#L39) specifies the 2-percentage-point accuracy margin, 95% interval, one-fifth cost target and 80% retained-answer comparison. The snapshot does not identify the individual who selected those values. Applying the criterion to the common method intersection and resampling companies were implementation choices documented in this review before paid testing.

The original criterion requires the accuracy bound plus either cost at most one-fifth of the comparator or higher accuracy among each method's most confident 80%. Higher retained-answer accuracy therefore satisfies the benefit test even when cost savings fall short of 5×. These historical project targets remain in a linked audit and machine-readable metrics. The [external report format](report-format.md) answers the task-level choice through measured accuracy, cost, speed, review tradeoffs and counterevidence; it adds no acceptance gates.

## Calibration needs precise names

Selected-answer Brier score and expected calibration error measure whether reported correctness probabilities match outcomes. Composite margins are ranking scores, not probabilities. Normalised composite scores can be compared with observed label distributions as a descriptive distance; that distance is named distribution agreement. Direct language models provide no full distribution, so their distribution agreement is unavailable rather than imputed.

Observed label distributions use one vote per filer within a statement. Conflicting labels within the same filer have already been deduplicated. They describe corpus variation rather than the correct posterior for a context-rich individual record.

## Execution preserves evidence

Freeze code, prompts, rules, template, sampling configuration and pricing before smoke inference. Never tune against benchmark answers. Store attempts, raw responses, usage, resolved model names, source hashes and original configuration. Unknown pricing or credentials stop execution before paid calls. Failed calls count as wrong; unknown billable usage is reported as unknown, never silently free.

The small profile must finish its repeats and option-order checks before a matching full run is allowed. Reports distinguish offline fixture checks from real benchmark evidence. The software generates an evidence-based interpretation separately from the original pass-rule fields.

## Sources establish the constraints

- [Original build brief](https://app.notion.com/p/3ec785996df481a7b824fde702c5614d)
- [Parent evaluation plan](https://app.notion.com/p/3ec785996df481d3898adc68e3049fb2)
- [SEC dataset scope and dimensional-data change](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)
- [SEC table definitions](https://www.sec.gov/files/financial-statement-data-sets.pdf)
- [TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python)
- [Vercel model catalog](https://ai-gateway.vercel.sh/v1/models)
