# Methodology

The study compares Jev, TypeSafe's fixed-choice decision model, with a conventional language model and programmed rules on repeated finance data-management decisions. Jev answers a fixed question by choosing from predefined answers and returns a probability for each answer. The comparison measures how often each method is correct, cost, speed, consistency, and how well each model's confidence score matches how often its answers are correct. Each run supplies its own dataset, model settings, results and conclusions.

The study reports one case at a time. The methodology does not depend on the case: a reader can apply it to a case of their own and use the results to choose between Jev and another method.

## Comparisons

| Comparison | What it tests | Why it matters |
| --- | --- | --- |
| Direct models versus programmed rules | One model call chooses the answer; rules match known patterns and can leave a record unanswered. | Models must add value beyond deterministic matching. |
| Wording only versus wording with context | The same records are tested with less and with more information. | The same wording can mean different things in different places. |
| Confidence scores | Answers are grouped by stated confidence and compared with how often they are correct. | A confidence score is only useful for setting a cut-off if it matches the share of answers that are correct. |
| Repeats and reordered options | The same question is repeated, or its answer options are reordered. | Inconsistent answers create reconciliation work. |

The conventional model returns an answer and a self-reported confidence. Jev also returns a probability for every offered answer. Results compare the complete tested workflows; they do not separate a model from its prompt or price.

## Cases and test scope

Each case has its own spec: the decision, source, answer key, model input, test scope and the patterns it tests. Current case: [statement mapping](cases/statement-mapping.md).

The test scope states which records are included. It can cover only part of the real task. Records are left out when they have no reliable answer key or fall outside the comparison, for example fields a template does not hold or record types the case does not test. The case spec documents the scope with counts from source to sample, the main groups left out and a worked example. Results apply to in-scope records only, and reports state the scope next to the main results.

A case can include a "not mapped" answer, so that recognising records that belong to no category is part of the task. If results are inconclusive, a later run can widen the scope. Scope changes are recorded in the case spec before inference.

## Architecture patterns

TypeSafe documents four [patterns](https://docs.typesafe.ai/patterns) for building with Jev. The study tests a pattern where it fits the case's decision, with one comparison per pattern.

| Pattern | What it does | How the study tests it |
| --- | --- | --- |
| [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing) | Acts on an answer only when its confidence is at or above a cut-off and sends the rest elsewhere. | Confidence cut-offs and calibration show whether the score can serve as the cut-off. Answers below a cut-off are compared with another model's answers on the same records. |
| [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) | Asks several questions about one record in one call; code uses the answers it needs. | The same questions are asked in one call and in separate calls. Results compare correct answers, cost and response time. |
| [Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) | Scores separate criteria, weights them in code and ranks candidates. | Tested in cases that rank candidates, such as matching a record against a register. |
| [Intent routing](https://docs.typesafe.ai/patterns/intent-routing) | Classifies a request first, then sends it to rules, a model or a person. | Tested in cases with distinct request types. |

## Metrics

- **Sample:** records are drawn at random from the in-scope records, so the mix of categories follows the data. The analysis reports how incorrect answers are spread across categories.
- **Correct:** an answer is correct when it matches the case's answer key. Failed calls and unanswered records count as incorrect. Rules also report the share of records they answer and how many of those answers are correct.
- **Same records:** two methods are compared on the records both were run on.
- **Record-level comparison:** for each pair of methods, reports count the records both answer correctly, both answer incorrectly, and only one answers correctly. Reports make no claim beyond the tested records.
- **Confidence:** for a set of confidence cut-offs, reports show how many answers are at or above each cut-off and how many of those are incorrect. Calibration compares stated confidence with the share of answers that are correct.
- **Cost:** the main cost measure is cost per 1,000 records for each method, from the tokens each call uses at uncached list prices in US dollars. Reports state the price source, date and per-token prices once, and compare how many input and output tokens each model uses per call. Runs record cost separately for the main comparison, the consistency checks and each pattern test. Costs are not invoices; integration and maintenance costs are excluded.
- **Speed:** the main speed measure is the median response time per record, measured under the reported concurrent load. Detailed analysis adds the slowest responses (95th percentile).
- **Consistency:** a random tenth of the sample is asked a second time, and a random tenth is asked with the answer options in a different order. Reports count the answers that change.

[Metric implementation](../benchmark/metrics.py).

## Conclusions

Each run gives a verdict on how useful Jev is for its tested kind of decision, based on the measured results. The verdict does not extend to other kinds of decision. No single cost multiple or accuracy cut-off decides practical value.

The answer key records the source's own judgement; it is not independently reviewed. Results on one source do not establish performance on other sources, other tasks or untested models. Synthetic, smoke and incomplete runs support no conclusions about model quality.

## Reports

Each run publishes three documents and an evidence file. The documents follow the same section order; each longer document adds detail rather than repeating the shorter one.

| Document | Reader | Content |
| --- | --- | --- |
| Summary | Management | One page: question and verdict, main results, confidence, where incorrect answers concentrate, next steps. Each section can become one slide. |
| Detailed report | Analysts and decision makers | The summary's sections in more depth, with real records as examples, plus test scope, record-level comparison, cost and speed, consistency, development effort and limits. |
| Appendix: methods and data | Anyone checking or rerunning the study | Case spec, sampling, prompts, model settings, price basis, results for every category, and a record of everything the run executed. |
| Evidence file | Reviewers and software | Every number and table in the documents, generated from the saved results. |

Writing rules for all three documents:

- Plain, descriptive headings and short sentences.
- "Correct" means the answer matches the answer key; it is defined once.
- Counts with their totals, such as 2,777 of 2,900, rather than percentages alone.
- Real records as examples, with the selection stated. Examples illustrate; they do not estimate how often something happens.
- No claims beyond the tested records, and no steps the study did not test.
- The documents describe the study as it is. Problems found along the way belong in the [development notes](development.md).

The structure draws on four published approaches to comparing models and documenting evaluations:

| Source | What it does | What this study takes from it |
| --- | --- | --- |
| [HELM](https://crfm.stanford.edu/helm/) (Liang et al., *Holistic Evaluation of Language Models*, Transactions on Machine Learning Research, 2023) | Measures accuracy, calibration, robustness, fairness, bias, toxicity and efficiency for every model on the same scenarios. | Several measures side by side for every method on the same records rather than accuracy alone: correct answers, calibration, consistency under repeats and reordered options, cost and speed. Fairness, bias and toxicity do not apply to this decision. |
| [Artificial Analysis](https://artificialanalysis.ai/methodology) | Compares models on quality, price and speed; computes cost per task from token use at listed prices. | Cost per 1,000 records from measured token use at stated list prices, and a typical (median) response time, reported next to quality. |
| Model cards (Mitchell et al., *Model Cards for Model Reporting*, FAT\* 2019) | Documents a model's details, intended use, metrics, evaluation data, results broken down by relevant factors, and caveats. | The appendix's methods part: model settings, the tested decision and scope, metrics, evaluation data, results by category and by wording group, and limits. |
| Datasheets for datasets (Gebru et al., *Datasheets for Datasets*, Communications of the ACM, 2021) | Documents a dataset's motivation, composition, collection process, preprocessing, uses and maintenance. | The case spec and the appendix's data part: source, how records were collected and filtered, what is in and out of scope, the answer key and its limits. |

The split into three lengths follows the study's readers rather than these sources.

Code generates every number, table and chart from the saved results. In the documents, generated content sits between `<!-- begin NAME -->` and `<!-- end -->` markers; regenerating a report refreshes those blocks without model calls. The text around the blocks is written for each study and checked against the evidence file.

## Evidence

Prompts, sampling and model settings are recorded before inference; predictions, usage and configuration are retained. Reports regenerate from that evidence without model calls.

Runs that tested the same records on the same data can be combined in one report, so a model can be added later without repeating the others. Each model's answers come from one run, and the appendix lists when each model's answers were collected, because a provider can change the model behind a name.
