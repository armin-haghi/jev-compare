# Backlog

Open questions for later runs. Each item is agreed as methodology before it is used in a report.

| Item | What to decide | Why it matters |
| --- | --- | --- |
| Differences between samples | How to judge whether a difference between two models would hold on other records, for example by repeating the test on a second, separate sample. The same applies to checking confidence cut-offs on records that were not used to set them. | Reports currently give record-level counts: records both models answer correctly, both incorrectly, and only one correctly. They make no claim beyond the tested records. |
| Common-practice baseline | Whether to add a reference method that answers with the category most companies use for the same wording. | It shows how much of the task a lookup of past mappings already solves, and where a model adds value. |
| Comparison model setup | Which conventional models and settings to compare, and how to obtain their confidence scores. | The current comparison uses one small model at its lowest reasoning setting. |
| Model behind a confidence cut-off | Whether sending answers below a confidence cut-off to a stronger model improves results. Depends on the comparison model setup. | Sending Jev's low-confidence answers to GPT-5 mini at its lowest reasoning setting does not change how many are correct. |
| Composite scoring case | A second case that ranks candidates, for example matching a reported company name to a register entry by name, address and identifier. | Composite scoring fits ranking decisions, which statement mapping does not have. |
| Development effort | How to describe what it takes to build and maintain each workflow, for example prompt and schema work, answer validation, and code needed around each model. | Model cost per 1,000 records is small for both models; building and maintaining the workflow may matter more to a team choosing between them. |
| Small run before a full run | Whether a full run should require a completed small run with identical code, settings and data. | The person running the study controls the budget; a required small run adds code and is not currently enforced. |
| Wider test scope | Whether to add lines a template absorbs into an existing category, such as general and administrative into SG&A. See the [statement mapping case](cases/statement-mapping.md). | Only needed if the comparison on the current scope is inconclusive. |
