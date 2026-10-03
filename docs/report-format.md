# Factsheets lead with the finding

Each run answers a practical question: how does Jev compare with the tested alternatives for this finance task? Lead with the measured finding, a task-specific recommendation and the total run cost. Keep the factsheet around 600 words; tables carry the comparisons.

## Evidence supports the recommendation

| Order | Required content |
| --- | --- |
| Finding and spending | An assertion supported by results; recommended workflow; total run cost and model split, distinguished from cost per 1,000 decisions. |
| Tested data | Task, source, dates, counts, category balance, difficult records and subset sizes. Define Jev for a new reader. |
| Main comparison | Matched accuracy counts, unit cost, response time, uncertainty, rules coverage and confidence-based review tradeoff. |
| Examples | A few saved successes and failures, with input context, expected category and both answers. Disclose selection; examples illustrate outcomes rather than estimate frequency. |
| Extra work | Why additional scoring was tested, actual calls per record, matched-subset results and cost. Say whether it helped. |
| Boundaries and sources | Counterevidence, unknowns that affect the recommendation, shared methodology and consolidated evidence links. |

Use plain task names such as “Choose a category” and “Score each category separately”. Headings state findings; they must change when the evidence changes. Incomplete runs, smoke checks and synthetic fixtures retain explicit limits and receive no deployment recommendation. Original acceptance targets remain in structured evidence, separate from the recommendation.

## Methodology stays separate from findings

The [methodology](methodology.md) defines workflows, scoring, uncertainty and scope once. The factsheet explains what this run found. Publication creates two files: factsheet.md and evidence.json. The evidence includes the run's preserved methodology text and hash, metrics, examples, configuration, provenance and raw-prediction hash.

The design follows [ONS guidance on chart text](https://service-manual.ons.gov.uk/data-visualisation/guidance/chart-text): concise, active titles describe the finding, with population and measurement details nearby. [Storytelling with Data](https://www.storytellingwithdata.com/blog/2017/3/22/so-what) recommends stating the takeaway explicitly. Here, small comparison tables connect the recommendation to its evidence without adding duplicate graphics or a narrative essay.

## Cleanup preserves the costly evidence

| Files reviewed | Decision |
| --- | --- |
| Seven economy-prefixed report files | Replace with one task-named factsheet and one evidence file. Metrics retain the curves and historical criterion; evidence embeds the methodology snapshot. |
| Original brief, design review and progress log | Move to docs/archive; preserve the parent proposal in a collapsed README section. |
| Smoke and prerequisite validation | Keep in the archive; remove the redundant generated smoke verdict from the active tree. Prior versions remain in Git. |
| Runner, case modules, tests and configurations | Keep: they implement or verify the study. Preserve frozen configuration names for reproducibility. |
| Local predictions, raw responses, downloaded sources and .venv | Keep outside Git: they preserve paid evidence, source provenance and the working runtime. |

Current output: [statement-mapping factsheet](../reports/statement-mapping-2026-10-02/factsheet.md) and [evidence](../reports/statement-mapping-2026-10-02/evidence.json).
