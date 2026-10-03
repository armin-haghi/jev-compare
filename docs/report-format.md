# Reports support a workflow choice

Each report answers: **How does Jev compare with the tested alternatives for this finance data-management task, and which workflow does the evidence support using?** Write for someone encountering Jev for the first time. Aim for a short main report; link detailed analysis separately.

## Four sections carry the argument

| Section | Required content |
| --- | --- |
| **The sample contains 2,900 records.** | Define the task and Jev in plain language. Show data source, dates, sample size, companies, categories, category balance, difficulty properties and the answer key. Distinguish the main sample from smaller checks. |
| **Tests compare decision workflows.** | Explain direct decisions, programmed rules and combined judgments. State what each comparison tries to find and why accuracy, cost, speed, confidence and consistency matter. |
| **Jev cuts direct costs 77%.** | Show accuracy with and without context, cost and speed. Explain uncertainty, rules' unanswered cases, confidence-based review and direct-versus-combined results on the same records. |
| **The evidence favors Jev direct.** | Recommend a tested workflow for the tested task. Give supporting evidence, counterevidence and scope limits. Link the detailed results, configuration and historical audit. |

Headings state each run's finding; the headings above illustrate the current test.

## Evidence determines the recommendation

- Show counts and denominators. Compare workflows on matching records.
- Separate observed accuracy differences from a statistically established advantage.
- Report rules' accuracy when they answer alongside their unanswered share.
- Show absolute and relative costs; identify unmeasured review and integration costs.
- Treat retaining 80% of answers as an illustration of review workload, not an acceptance gate.
- Include an alternative's strength or a weakness in the recommended workflow.
- Preserve original criteria in a linked historical audit. Add no numerical pass/fail gates.
- Synthetic, smoke and incomplete runs do not support deployment recommendations.

## Saved outputs generate both versions

The command-line summary gives dataset, purpose, result and recommendation. The main report stays concise; a linked detail report contains category breakdowns, stability checks, costs and charts. Both versions and the shareable evidence package use the same saved predictions and renderer. Regeneration makes no model calls.

See the [current report](economy-report.md), [detailed analysis](economy-details.md) and [evidence snapshot](economy-validation.json).
