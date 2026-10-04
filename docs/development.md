# Development notes

Problems found in the first statement-mapping run (2026-10-02) and its reports, and how to avoid them in later runs.

## Study design

| Problem | Effect | Avoid by |
| --- | --- | --- |
| Acceptance thresholds were set before the study, without a link to the question being tested: a 2-point accuracy margin, a one-fifth cost target and the most confident 80% of answers. | The thresholds were computed and reported alongside the findings and confused readers. They were removed. | Agree the question first. Add a threshold only when it follows from that question. |
| A check combined every method's records before comparing two methods. | Variants that ran on 100 records reduced a 2,900-record comparison to 100 records. | Compare each pair of methods on the records both were run on. |
| One arbitrary point (each model's most confident 80% of answers) was reported as a finding. | Readers could not tell where the number came from or why it mattered. | Show the full table of confidence cut-offs instead of a single chosen point. |
| A simulated uncertainty range was added without first agreeing the method. | The range needed lengthy explanation and was removed. | Agree a method in the methodology before using it; keep open methods in the [backlog](backlog.md). |
| Four combined-scoring variants scored every category on wording and position, and code combined the scores. | They took 58% of the run's cost, were hard to explain and did not improve on asking for the category directly. The GPT-5 mini version gave tied top scores on 84 of 100 records. The design also differed from TypeSafe's documented use of composite scoring, which ranks candidates. | Test a pattern only in its documented form and where it fits the decision. Try a new design on a few records for each model before a paid run. |
| The sample took the same number of records from each category. | Overall accuracy gave rare, hard categories the same weight as common ones, so it did not describe a typical statement. | Sample at random from the test scope and report overall accuracy. Check in the analysis whether any category accounts for most failures. |
| The repeat and reordered-option checks used 20 records each. | One changed answer moved the result by 5 points, so the checks could only catch large instability. | Size checks so that a single record moves the result by well under a point; at these prices that costs little. |
| The test scope came from the template's tag list without being documented. | Readers could not see that most statement lines were outside the test. | Document scope with counts and an example in the case spec before the run. |

## Data preparation

| Problem | Effect | Avoid by |
| --- | --- | --- |
| Duplicate removal used company, statement and wording as its key. | 5,964 lines with repeated wording inside one filing were dropped, for example several lines worded "Other" in different balance-sheet sections. | Check what a deduplication key removes before freezing a dataset. |

## Reporting

| Problem | Effect | Avoid by |
| --- | --- | --- |
| Agreement with the filed tag was reported as accuracy, without describing how consistent the tags are. | Readers could read 96% as "4% wrong". | Define "correct" once, and report how consistent the answer key is. |
| Headings stated claims, and some wording implied steps the study did not test, such as human review. | Reports read as advocacy rather than findings. | Use plain, descriptive headings and describe only what was tested. |
| One category was singled out as "counterevidence" because it had the largest gap of 29 categories. | A selected extreme was presented as a finding. | Report all categories in a table. |
| The published evidence file was edited by hand, and the report generator carries existing fields forward. | Removed results stayed in the evidence file after regeneration. | Generate evidence files only from code; do not edit them by hand. |
