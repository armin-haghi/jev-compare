# The study compares decision workflows

The study asks how Jev compares with alternatives for repeated finance data-management decisions. Jev selects from predefined answers and returns probabilities. The comparison measures accuracy, cost, speed, consistency and the usefulness of confidence for directing human review. Each run supplies its own dataset, model configurations, results and recommendation.

## Workflows expose different tradeoffs

| Comparison | What it tests | Why it matters |
| --- | --- | --- |
| Direct models versus programmed rules | One model call selects the final answer; rules match known patterns and can abstain. | Models must add value beyond deterministic matching. |
| Labels versus surrounding context | The same records are tested with less or more information. | Finance labels can mean different things in different statements. |
| Confidence-based deferral | Low-confidence answers are set aside and errors in retained answers are counted. | Uncertain mappings can be directed to review. |
| Direct versus combined judgments | Smaller judgments are combined in code, using bundled or separate calls. | Extra calls and scoring logic must justify their cost. |
| Repeats and reordered options | The same task is repeated or its answer options are reordered. | Inconsistent decisions create reconciliation work. |

The conventional direct model returns a category and self-reported confidence. Jev direct also returns probabilities for every offered answer. Results compare the complete tested workflows; they do not isolate model architecture from prompting or pricing.

## Statement mapping fixes the task

The financial-statement case uses public United States Securities and Exchange Commission (SEC) filings. A company's filed accounting tag maps to the answer key and is withheld from model input. For example, “Other income, net” can refer to total non-operating income or a component; neighbouring lines help distinguish the categories.

Every record receives the candidate categories for its statement. The label condition supplies wording and statement type. Context adds up to two neighbouring lines on each side, amount sign and relative size, and industry description.

We test whether smaller questions help either model. Instead of “Which category is this?”, ask two questions for every possible category: “Does the wording fit?” and “Do the surrounding lines fit?” Code adds a numerical-fit score and chooses the highest-scoring category. The [original brief](https://github.com/armin-haghi/jev-compare/blob/e05b745/docs/build-brief.md#L424) specifies testing these questions together in one call and separately, one call per question. Separate calls resend the record and candidate information, increasing token use and cost.

Each component uses a 0–4 scale; the final score weights the three components equally. Jev uses its most probable score level. Fixed template order breaks ties. These are specific implementations, not every possible way to combine judgments. [Implementation](https://github.com/armin-haghi/jev-compare/tree/581a59b/benchmark/methods).

## Metrics preserve the comparison

- **Accuracy:** agreement with the answer key, counting failed calls and abstentions as wrong. Rules also report their answered share and accuracy among answers, distinguishing unresolved work from wrong emitted labels.
- **Matched samples:** direct methods use the main sample. Combined workflows can use a smaller nested subset; comparisons between workflows use their shared record IDs.
- **Uncertainty:** paired accuracy differences include a 95% interval obtained by resampling companies, accounting for multiple records from one company. An interval spanning zero does not establish accuracy superiority.
- **Review tradeoffs:** each method retains its own most confident answers. Retaining 80% is an illustration from the measured curve, not a deployment target. Accepted subsets can differ; human-review outcomes and costs are not measured. Combined-score margins rank answers but are not correctness probabilities.
- **Cost and speed:** costs use measured tokens at uncached list prices in United States dollars. Latency includes execution overhead under the reported concurrent load. These are not invoices or throughput guarantees; integration and maintenance costs are excluded.
- **Consistency:** changed answers are counted over the reported repeat and option-order subsets. Small checks do not establish universal stability.

[Metric implementation](https://github.com/armin-haghi/jev-compare/blob/581a59b/benchmark/metrics.py).

## Recommendations follow the evidence

Each run recommends a workflow for its tested task, using observed tradeoffs and counterevidence. No universal cost multiple or accuracy cutoff decides practical value. Original acceptance targets remain in the run's historical audit.

Category-balanced samples do not estimate a natural production mix. Filed tags are a proxy for independently reviewed accounting truth. Public filings do not establish performance on private management accounts, other finance tasks or untested models. Synthetic, smoke and incomplete runs do not support deployment recommendations.

Prompts, sampling and model settings are recorded before inference; predictions, usage and configuration are retained. Reports regenerate from that evidence without model calls. A methodology snapshot accompanies each generated report so its definitions remain inspectable.
