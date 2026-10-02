# Tests verify the local build

Repository: https://github.com/armin-haghi/jev-compare

| Stage | Evidence |
| --- | --- |
| Source preservation and review | e05b745 preserves the parent page and build brief and records study corrections. |
| Data and methods | bed9803 implements the 29-line case, preparation and decision methods. |
| Execution and reporting | 6086536 adds the runner, metrics, coverage charts and independent fixture case. |
| Validation | 31 tests pass with Python 3.12 and locked dependencies. |
| Offline demonstration | All ten method/model combinations produce 160 synthetic prediction rows, repeats, shuffle results and reports. |
| SEC preparation | 21 archives totaling 2.2 GB produce 148,422 eligible rows; all 29 categories have at least 1,375 rows. |
| Live discovery | The Gateway catalog name is typesafe-ai/jev; the TypeSafe-compatible request model is jev. |
| Live smoke | Run 20261002T220450Z-7bcbffd4 completed 354 outputs and 1,996 requests in 544 seconds, with zero final failures and $0.286157348 in list-price cost. |

## The smoke excludes frontier models

Credentials and the SEC contact header are configured locally. The initial live smoke uses GPT-5 mini, Jev and rules, with a $1 software limit inside the user's $10 key limit. Frontier inference requires explicit authorization and the --allow-frontier flag.

The completed smoke cost $0.23698925 for GPT-5 mini and $0.049168098 for Jev at configured list prices. An earlier interrupted attempt recorded $0.0002375 of additional known usage. A $4.96 conservative budget reservation in that interrupted attempt was not measured billing; output now distinguishes reservations from known usage.

Jev required 28 retries because its rounded probability vectors sometimes summed to 0.99 or 1.01. The corrected validator accepts rounding residuals bounded by the number and precision of entries. All 2,252 stored probability vectors pass offline replay; no further inference was needed for this correction. The original smoke artifacts retain the retry costs.

The structured validation summary is [smoke-validation.json](smoke-validation.json). Detailed local artifacts are under results/20261002T220450Z-7bcbffd4/.

## Jev warrants a larger test

The automatically generated verdict is preserved in [smoke-verdict.json](smoke-verdict.json) and included after the tested dataset properties in the local report and in management_summary.json. On the 29 context-rich direct decisions, Jev scored 27/29 versus 26/29 for GPT-5 mini, at 23.1% of its estimated per-record cost. The one-record lead and five-record composite subset do not establish a winner or the study pass rule. The separate-question GPT scoring protocol needs review before its poor result is used for model comparison. The concise verdict appears in the standard command output and regenerates from the saved predictions, with their hash attached.

The 444-entry SEC industry list is committed. Dataset preparation emits a mapping-review queue; no additional tags were silently added to the frozen answer key.

## The study has explicit limits

The parent plan's 28-line taxonomy becomes 29 lines so that total and component non-operating income remain distinct. Selected-answer calibration and population-distribution agreement are separate metrics. Reports mark fixture, smoke and incomplete runs as non-evidence.

The complete small and full study profiles have not run. Smoke results test integration and execution; they do not establish a model-quality conclusion. Gateway model aliases may expose a requested model name without an immutable underlying weight version.

## The larger run excludes frontier

The economy configuration retains all seven methods, using GPT-5 mini, Jev and rules. A 58-record prerequisite precedes 2,900 records balanced across 29 categories; composite methods use 100 records. Estimated combined list-price cost is $4.95, based on the stored smoke. New software limits total $6 inside the existing $10 key limit. Eight records run concurrently, with four questions per record; a shared reservation ledger bounds spending. Prompts and the answer key remain frozen.
