# Reports support a workflow choice

Each report answers: **How does Jev's approach compare with the tested alternatives for this finance data-management task, and which workflow does the evidence support using?** The reader needs no prior knowledge of Jev, the benchmark or earlier reports.

Jev is a model used to choose from predefined answers and return probabilities. This study compares that approach with a conventional language model and programmed rules. A result describes the tested models, prompts, task and data; it does not isolate the cause of a model's performance or establish superiority across finance.

## The dataset opens the report

Use the following order for every report. Headings state the finding for that run; example headings below illustrate the current financial-statement task.

| Order | Content | Required evidence | Reader's decision |
| --- | --- | --- | --- |
| 1 | **The sample contains 2,900 records.** Introduce the task and show dataset properties before results. | Source, dates, unit of observation, eligible and sampled counts, companies, answer categories, balance, difficulty properties, answer-key provenance, and sample sizes for each comparison. | Determine whether the data resembles the intended workload. |
| 2 | **The study compares decision workflows.** Explain Jev, the alternatives, model inputs and each test's purpose. | Exact tested model names; direct choice versus combining smaller judgments; rules; label-only versus contextual input; one concrete task example. | Understand what the experiment can distinguish and why it matters. |
| 3 | **Jev cuts direct costs 77%.** Compare the main decision methods, including where they struggle. | Correct answers and denominators, accuracy, unanswered records, cost per 1,000, median and slow-tail latency; paired accuracy uncertainty; rules' answered-only accuracy; context effects; difficult subsets and categories. | Weigh accuracy, cost, speed and unresolved work without collapsing them into a pass/fail label. |
| 4 | **Confidence separates correct answers.** Explain what happens when low-confidence decisions go to review. | Retained and deferred counts, remaining errors and accuracy for each method; explain differing accepted subsets and unmeasured human-review outcomes. | Assess the usefulness of confidence for routing work. |
| 5 | **Direct choices outperform combined scores.** Compare direct and multi-question workflows on the same records. | Common record count; accuracy, cost and ties for every tested workflow; repeat and answer-order checks with denominators. | Decide whether decomposition adds value over a direct decision. |
| 6 | **The evidence favors Jev direct.** Give a scoped recommendation and explain the alternatives. | Reasons tied to the tables; opposing evidence; conditions where rules or the language model remain appropriate; explicit limits to generalization. | Choose a starting workflow for this task and understand the remaining uncertainty. |
| 7 | **Saved evidence supports these findings.** Provide reproducible evidence and operational context. | Run identity, completed outputs, calls, costs by model, pricing basis, data and prediction hashes, configuration, detailed metrics and material limitations. | Verify the claims and distinguish measured results from assumptions. |

## Each test answers a decision

| Test | What it tries to find | Why the finding matters |
| --- | --- | --- |
| Direct classification versus rules and a language model | Accuracy, cost and speed when each workflow handles the same record. | A model must earn its place beyond deterministic matching. |
| Label-only versus surrounding context | Whether neighbouring lines and numerical context help resolve the label. | Finance labels can have different meanings in different statements. |
| Confidence-based deferral | Whether uncertain answers contain a disproportionate share of errors. | A team can route doubtful mappings to review; review cost and final quality require separate measurement. |
| Multiple judgments combined in code | Whether decomposition improves the final decision enough to justify extra work and calls. | Jev's small-decision approach can be used directly or as components of a larger workflow. |
| Repeated calls and reordered answers | Whether an unchanged task yields a changed decision. | Inconsistent mappings create reconciliation work. |

## Recommendations follow measured tradeoffs

- State the preferred **tested workflow for the tested task**, with the observations that support it. Keep observed accuracy differences separate from evidence that establishes a reliable accuracy advantage.
- Show rules' coverage and accuracy when they answer. Abstention counts as unresolved work, not an incorrect emitted label. Preserve the benchmark's overall score, which counts abstentions as wrong, and explain that convention.
- Compare direct and composite workflows on their shared records. A 100-record composite result cannot be ranked against a 2,900-record direct result as though they used the same sample.
- Express both relative and absolute costs. Four times cheaper can be useful; its business value also depends on volume, error costs and integration costs, which this benchmark does not measure.
- Show evidence against the recommendation, such as categories where the alternative performs better, unresolved errors and sensitivity to the scoring protocol.
- Describe confidence-based deferral as an observed routing tradeoff. An 80% retained share is an illustration from the measured curve, not a deployment target or an acceptance gate.
- Preserve original study criteria in a linked historical audit and machine-readable metrics. Do not introduce numeric gates or use the old criterion to substitute for the task-level recommendation.
- In synthetic, smoke or incomplete runs, identify the evidence status before interpreting any numbers. These runs do not support a deployment recommendation.

## The current evidence supports scope

The 2,900-record test supports Jev direct as a preferred model workflow for mapping these public financial-statement labels: with context it achieved 95.76% accuracy versus GPT-5 mini's 95.24%, at $0.0580 versus $0.2510 per 1,000 records. The accuracy-difference interval includes zero, so the recommendation rests on the observed cost, speed and confidence tradeoffs, not proven accuracy superiority. On the shared 100-record subset, both direct models scored 98%; Jev's multi-question variants scored 94–95%, giving no observed accuracy benefit from decomposition. [Evidence: completed-run snapshot](economy-validation.json).

The report must also show the counterevidence: rules answer a subset accurately, some categories favor GPT-5 mini, and the answer key consists of company-filed tags rather than independently reviewed accounting judgments. The tested task is one part of finance data management; entity matching, loan classification and untested models remain outside this result.

## Standard output follows this order

The full report and its machine-readable analysis follow this format. The command-line summary compresses the same sequence into dataset, purpose, result and recommendation, followed by the cost and report path. It does not print a historical pass/fail flag as the conclusion.

Reports regenerate from saved predictions without model calls. Figures and the shareable report use the same renderer and evidence as local output, preventing a manually written summary from drifting from future runs. The original [evaluation plan](../README.md) and [build brief](build-brief.md) remain preserved as source documents.
