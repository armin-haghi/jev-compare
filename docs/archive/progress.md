Archived implementation history. Current findings: [statement-mapping factsheet](../../reports/statement-mapping-2026-10-02/factsheet.md).

# Tests verify the local build

Repository: https://github.com/armin-haghi/jev-compare

| Stage | Evidence |
| --- | --- |
| Source preservation and review | e05b745 preserves the parent page and build brief and records study corrections. |
| Data and methods | bed9803 implements the 29-line case, preparation and decision methods. |
| Execution and reporting | 6086536 adds the runner, metrics, coverage charts and independent fixture case. |
| Validation | 37 tests pass with Python 3.12 and locked dependencies. |
| Offline demonstration | All ten method/model combinations produce 160 synthetic prediction rows, repeats, shuffle results and reports. |
| SEC preparation | 21 archives totaling 2.2 GB produce 148,422 eligible rows; all 29 categories have at least 1,375 rows. |
| Live discovery | The Gateway catalog name is typesafe-ai/jev; the TypeSafe-compatible request model is jev. |
| Live smoke | Run 20261002T220450Z-7bcbffd4 completed 354 outputs and 1,996 requests in 544 seconds, with zero final failures and $0.286157348 in list-price cost. |

## The smoke excludes frontier models

Credentials and the SEC contact header are configured locally. The initial live smoke uses GPT-5 mini, Jev and rules, with a $1 software limit inside the user's $10 key limit. Frontier inference requires explicit authorization and the --allow-frontier flag.

The completed smoke cost $0.23698925 for GPT-5 mini and $0.049168098 for Jev at configured list prices. An earlier interrupted attempt recorded $0.0002375 of additional known usage. A $4.96 conservative budget reservation in that interrupted attempt was not measured billing; output now distinguishes reservations from known usage.

Jev required 28 retries because its rounded probability vectors sometimes summed to 0.99 or 1.01. The corrected validator accepts rounding residuals bounded by the number and precision of entries. All 2,252 stored probability vectors pass offline replay; no further inference was needed for this correction. The original smoke artifacts retain the retry costs.

The structured validation summary is [smoke-validation.json](smoke.json). Detailed local artifacts are under results/20261002T220450Z-7bcbffd4/.

## Jev warrants a larger test

The automatically generated verdict is preserved in [smoke-verdict.json](https://github.com/armin-haghi/jev-compare/blob/f8b0561/docs/smoke-verdict.json) and included after the tested dataset properties in the local report and in management_summary.json. On the 29 context-rich direct decisions, Jev scored 27/29 versus 26/29 for GPT-5 mini, at 23.1% of its estimated per-record cost. The one-record lead and five-record composite subset do not establish a winner or the study pass rule. The separate-question GPT scoring protocol needs review before its poor result is used for model comparison. The concise verdict appears in the standard command output and regenerates from the saved predictions, with their hash attached.

The 444-entry SEC industry list is committed. Dataset preparation emits a mapping-review queue; no additional tags were silently added to the frozen answer key.

## The study has explicit limits

The parent plan's 28-line taxonomy becomes 29 lines so that total and component non-operating income remain distinct. Selected-answer calibration and population-distribution agreement are separate metrics. Reports mark fixture, smoke and incomplete runs as non-evidence.

The economy small and full profiles are complete. The original configuration specifies 8,700 main records and 1,500 composite records; this budgeted run uses 2,900 and 100 respectively. The original smoke remains an integration check. Gateway model aliases may expose a requested model name without an immutable underlying weight version.

## The larger run excludes frontier

The economy configuration retains all seven methods, using GPT-5 mini, Jev and rules. A 58-record prerequisite precedes 2,900 records balanced across 29 categories; composite methods use 100 records. Estimated combined list-price cost is $4.95, based on the stored smoke. New software limits total $6 inside the existing $10 key limit. Four records run concurrently, with two questions per record; a shared reservation ledger bounds spending. Prompts and the answer key remain frozen.

The first concurrent prerequisite (20261002T223602Z-77b838c0) stopped at its $1 budget after connection errors. Recorded usage was $0.479136; conservative accounting including unknown requests was $0.8579825. The retry lowers request concurrency from 32 to eight and reduces the GPT-5 mini output ceiling from 4,096 to 1,024 tokens. Saved successful completions use fewer than 1,024 output tokens. The next prerequisite and larger run retain $1 and $5 limits; total new limits including the interrupted run are $7, below the existing key cap.

The reduced-concurrency prerequisite (20261002T230901Z-02e0cb22) completed all seven methods: 720 outputs, 4,964 requests, no failed outputs or unknown usage, and $0.71816821 in list-price cost. Its mechanism checks passed. The larger run uses the same freeze and a $5 software limit.

## The larger test confirms competitiveness

The [economy report](../../reports/statement-mapping-2026-10-02/factsheet.md) leads with the tested dataset: 2,900 records, 29 equally sampled categories, 2,304 filers, fiscal years 2021–2025, and a 100-record composite subset. Run 20261002T232137Z-571ebdd4 completed 18,760 outputs and 28,568 requests with zero failures or unknown usage. GPT-5 mini cost $3.46297875; Jev cost $0.720991908. The 5,152.8-second run stayed within its $5 limit. The [validation snapshot](../../reports/statement-mapping-2026-10-02/evidence.json) preserves the audit, configurations, metrics and cost ledger.

With context, Jev scored 2,777/2,900 (95.76%) versus GPT-5 mini's 2,762/2,900 (95.24%), at 77% lower direct-call cost (4.3× cheaper). This observed cost–accuracy result favors Jev for direct classification on the tested dataset. The paired filer-cluster 95% interval for the accuracy difference spans −0.14 to +1.20 percentage points, so the observed lead does not establish superiority. Composite scoring ties warrant protocol review before selecting a method.

Standard output and reports separate this practical interpretation from the original acceptance criterion. The numeric cutoffs came from the imported brief; the common-subset and company-resampling choices came from implementation. The unchanged criterion remains unmet on its 100-record subset because its interval extends beyond the allowed 2-point accuracy loss. Higher accuracy among the most confident 80% satisfies the alternative benefit test, so the 5× cost target is not the blocker. Reporting changes use saved outputs and add no inference charges.

All recorded runs total $5.667669716 in known list-price usage. The interrupted concurrent prerequisite also has $0.3788465 of unknown-call reservations, which are not measured charges. Frontier inference remains excluded. The audit verified sample membership, category balance, output uniqueness, source hashes and model identities.

## Reports support an external reader

The [methodology](../methodology.md) explains the shared workflows, scoring and uncertainty. The [report format](../report-format.md) keeps each run focused on its dataset, findings and recommendation. The generated [economy report](../../reports/statement-mapping-2026-10-02/factsheet.md) stays short; [detailed analysis](../../reports/statement-mapping-2026-10-02/evidence.json) contains its breakdowns and charts. Both link the general methodology instead of repeating it. A preserved methodology snapshot and hash accompany each run. The historical criterion is archived separately and no longer appears as the command-line conclusion.

The recommendation favors Jev direct for the tested mapping task. It also records the limits: some categories favor GPT-5 mini; rules answer a subset accurately; Jev's tested combinations add cost without improving accuracy over direct choices on their shared sample. Reports are generated from stored evidence; no additional inference was run. The same renderer produces local and shareable output, with its structured evidence in analysis.json. All 42 tests pass, including matched-subset reversals, rules' abstention denominators, confidence deferral counts, unknown-cost handling and shared-report evidence consistency.

Method labels now state the action requested, and comparison tables show observed calls per record. GPT-5 mini's separate category-scoring version made 28–30 calls per record, scored 9/100 with context and cost $6.7496 per 1,000 records. Its final-category call scored 98/100 on those records at $0.2514 per 1,000. The methodology explains why the brief included this comparison; the updated report adds no inference or new experimental conditions.
