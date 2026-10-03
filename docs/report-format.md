# Methodology and findings stay separate

The [methodology](methodology.md) explains the study question, workflows, task setup, scoring, uncertainty and limits once. It contains no run-specific winners, costs or sample sizes.

## Run reports explain the findings

| Part | Content |
| --- | --- |
| Dataset | Task, tested models, source, dates, counts, category balance, difficult records and subset sizes. Link the methodology instead of repeating it. |
| Findings | Measured accuracy, cost, speed and review tradeoffs; notable failures, category differences and whether combined judgments helped. Keep denominators and uncertainty beside the results. |
| Recommendation | Preferred tested workflow, supporting evidence, counterevidence and limits that affect this run's interpretation. |

Headings state the run's findings. Keep the main report short and dataset-first. A linked detail report contains the run's full breakdowns and figures, without repeating general method explanations.

Label methods by what the model was asked to do, such as “Choose a category” or “Score each category in separate calls”. Show observed calls per record beside cost; give a one-sentence reason for a comparison where the table would otherwise be opaque.

## Evidence keeps reports reproducible

The same renderer produces local and shareable reports from saved predictions. Each package includes a methodology snapshot and hash, configurations, metrics and raw-evidence hashes. Historical criteria remain in a linked audit, separate from the recommendation. Command output gives the dataset, task, result and recommendation.

See the [current report](economy-report.md), [run details](economy-details.md) and [evidence snapshot](economy-validation.json).
