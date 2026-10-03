# The original criterion remains archived

## The brief sets acceptance targets

The original criterion requires an accuracy loss no greater than 2 percentage points at the lower end of a 95% interval, plus either cost at most one-fifth of the comparator or higher accuracy among the most confident 80% of answers.

Source: [brief as imported before implementation](https://github.com/armin-haghi/jev-compare/blob/e05b745/docs/build-brief.md#L39). The snapshot does not identify who originally selected the cutoffs.

The implementation applies the criterion to records shared by Jev direct and all conventional-model methods, and resamples companies to account for correlated records.

These are project acceptance targets. Practical value is assessed separately from measured accuracy, cost and uncertainty.

| Context | Shared records | Accuracy-difference interval | Cost relative to comparator | Higher accuracy at 80% coverage | Original criterion |
| --- | ---: | --- | --- | --- | --- |
| label only | 100 | -6.06 to +2.00 points | 23.1% (target ≤20%) | Yes | Unmet |
| with context | 100 | -3.00 to +3.00 points | 23.1% (target ≤20%) | Yes | Unmet |

The shared-sample interval extends below the allowed 2-point loss. That explains the unmet original criterion; the full direct comparison above uses its own larger sample and interval.

Where retained-answer accuracy is higher, that satisfies the alternative benefit test; the 5× cost target is not required. Each method retains its own most confident 80%, so accepted records can differ.

