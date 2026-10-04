Archived. The original evaluation proposal, before the build brief. Current study: [methodology](../methodology.md).

Source: [original parent evaluation plan](https://app.notion.com/p/3ec785996df481d3898adc68e3049fb2?pvs=204).

**What:** Evaluation plan for Jev, TypeSafe's decision model, against conventional LLM workflows on repeated finance data decisions. The aim is to find the kind of decision where Jev is the better building block, not to replace LLMs in general.
**Status:** Case 1 (mapping company financial-statement lines to a standard template, using public SEC data) agreed on 2 Oct 2026 and specified in the build brief below. Earlier ESEF framing retired.
**Next step:** Hand the build brief to a coding agent. Run the small profile first.
# Objective: find where Jev beats LLMs
Jev reads text or structured data and answers a fixed question with one of a fixed list of options, a probability for each option, and a confidence number. It writes no explanation. TypeSafe positions it as a component inside ordinary software: code owns the workflow and the rules, and Jev supplies the small judgments the code cannot make, such as which category a messy record belongs to.
This evaluation tests whether that component beats a conventional LLM call on the decisions a finance data-management team makes thousands of times: matching, classifying and mapping records that arrive with inconsistent wording.
Reference: [TypeSafe: How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)
## Hypothesis: Jev wins on bounded, repeated decisions
Jev should do well when:
- the answer comes from a fixed list;
- the same decision repeats across many records;
- several separate clues contribute, and code can combine them;
- the confidence number is reliable enough to decide which answers need a person.
The comparison is against four alternatives on the same records: a rules baseline (keyword and position rules, no model), a small LLM, a frontier LLM, and Jev. The LLMs run two ways: one direct call, and a decomposed version that scores clues separately and lets code combine them, which is Jev's own pattern.
# Case 1: map statement lines to a template
Every US listed company files annual financial statements with the SEC. Each line on those statements carries two things: the company's own wording, and a standard tag the company attached to say what the line is. The tag is public but, in this test, hidden from the model.
**The question:** given one line as the company wrote it, which of 28 standard template lines is it?
**The answer key:** the company's own tag, mapped to a template line.
## How the test works
1. Download the SEC tables that hold every statement line, its wording and its tag.
2. Build one record per line and hide the tag.
3. Ask each system the same question: which template line is this?
4. Reveal the tag and score every answer.
5. Compare the systems on accuracy, cost, speed, repeatability, and whether their confidence separates right answers from wrong ones.
The run starts small, a few hundred records, to prove the mechanism, then moves to the full set for results.
## Example: one wording, two answers
Real lines from FY2024 annual reports. Both companies wrote "Other income, net". The neighbouring lines decide what it is.
| Company | Lines as filed, in order | Template line | Why |
| --- | --- | --- | --- |
| NETGEAR | Income (loss) from operations 12,216 → Other income, net 12,672 → Income (loss) before income taxes 24,888 | Total non-operating income | The only line between operating income and pre-tax income, so it includes interest |
| Veru | Operating loss → Interest expense 607,470 → Other income, net 861,619 → Total non-operating income (expenses) (160,928) → Loss before income taxes | Other non-operating income | A component listed beside interest expense, under a separate total |
| SITE Centers | Under the heading "Revenues from operations": Fee and other income 8,181 | Revenue | "Other income" under a revenue heading is revenue |
## Why this case is hard enough
- **Close neighbours.** The 28 template lines sit a few rows apart within one statement. "Accrued expenses and other current liabilities" fits two lines that share the same section, sign and period; wording and position must separate them.
- **Measured ambiguity.** Thousands of companies use the same wording. Where they attach different tags to it, the data itself marks the label as ambiguous and records how the companies split. Jev's probabilities can be checked against that split.
- **Rules first.** A keyword-and-position baseline runs before any model. Every method is scored on the records the baseline gets wrong, which is where a model earns its place.
## Why it resembles real work
Portfolio companies and borrowers send management accounts with their own line wording. Analysts map those lines into a fixed template before any analysis. The decision, the ambiguity and the volume are the same as in this case.
# Later cases: same harness, new question
The harness is built so a new case replaces case 1 without changing the runner, methods or metrics.
| Case | Question | Answer key | Example |
| --- | --- | --- | --- |
| 2. Entity matching | Is this reported name the same legal entity as this register record? Yes or no. | The legal entity identifier (LEI) a fund reported alongside the name | "HCA, Inc., 3.50%, 9/1/30" as reported by a fund, against the register's HCA Healthcare Inc. (the parent) and HCA Inc. (the subsidiary that issues the bonds) |
| 3. Loan type | What type of loan is this: first lien, second lien, unitranche, subordinated, preferred equity, common equity, other? | The lending fund's own type label, mapped to the fixed list | Doxim, Inc., L + 6.00%, 1.00% floor, matures 02/28/24, filed by Goldman Sachs BDC as "1st Lien/Last-Out Unitranche" |
# Outputs: evidence, summary, chart
- A benchmark run with record-level predictions, so any aggregate can be recomputed and any individual decision inspected.
- A management summary file with the plain-words case description, counts, results by method and by slice, the pass-rule outcome, cost and latency, and representative examples.
- The headline chart: share of records a system decides on its own (x axis) against its error rate on those records (y axis), one line per method.
# Build brief
The sub-page below specifies repository structure, data retrieval, the 28-line template, method implementations, metrics, result schemas, commands and acceptance checks, so a coding agent can build the benchmark without choosing experiment semantics.
[Build Brief: Reusable Jev Benchmark](https://app.notion.com/p/3ec785996df481a7b824fde702c5614d)
