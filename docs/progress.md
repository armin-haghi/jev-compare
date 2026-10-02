# Tests verify the local build

Repository: https://github.com/armin-haghi/jev-compare

| Stage | Evidence |
| --- | --- |
| Source preservation and review | e05b745 preserves the parent page and build brief and records study corrections. |
| Data and methods | bed9803 implements the 29-line case, preparation and decision methods. |
| Execution and reporting | 6086536 adds the runner, metrics, coverage charts and independent fixture case. |
| Validation | 28 tests pass with Python 3.12 and locked dependencies. |
| Offline demonstration | All ten method/model combinations produce 160 synthetic prediction rows, repeats, shuffle results and reports. |

## Live execution needs credentials

The real SEC corpus and paid benchmark have not run. Set AI_GATEWAY_API_KEY and SEC_USER_AGENT in .env and choose a spending limit. Vercel routes all three configured models, including Jev; a separate TypeSafe key is optional.

Preparation automatically fetches the SEC industry list if absent. Commit the generated cases/sec_lines/sic_codes.json before inference. The template-extension queue remains unreviewed until real corpus reconnaissance exists.

## The study has explicit limits

The parent plan's 28-line taxonomy becomes 29 lines so that total and component non-operating income remain distinct. Selected-answer calibration and population-distribution agreement are separate metrics. Reports mark fixture, smoke and incomplete runs as non-evidence.

Live provider compatibility, real SEC availability, corpus size and model performance remain unmeasured. Gateway model aliases may expose a requested model name without an immutable underlying weight version.
