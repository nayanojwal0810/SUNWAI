# Business and statistical findings

## What we checked

This analysis uses 115,961 complaints received in 2019 with a known reported-relief outcome. We looked at whether product differences were clear, how precise the rates are, and whether the company comparison changed when we used a shorter time period.

## Differences between products

| Product | Labeled complaints | Reported relief | Estimated 95% interval |
| --- | ---: | ---: | --- |
| Mortgage | 9,389 | 6.43% | 5.95%–6.95% |
| Debt collection | 21,824 | 11.51% | 11.10%–11.95% |
| Credit reporting | 55,047 | 21.66% | 21.32%–22.00% |
| Credit card or prepaid card | 11,533 | 28.16% | 27.35%–28.99% |
| Checking or savings account | 6,884 | 28.36% | 27.30%–29.43% |

We used Wilson confidence intervals to show uncertainty around each rate. The intervals above are fairly narrow because the sample sizes are large. They assume a simplified model of independent observations; repeated narratives and selection into this dataset can weaken that assumption.

## Statistical test

A chi-square test compared reported relief with product category.

| Measure | Result |
| --- | ---: |
| Chi-square statistic | 3,595.85 |
| Degrees of freedom | 8 |
| P-value | Below 0.0001 |
| Cramér's V | 0.1761 |

The result suggests an association between product category and reported relief in this sample. Cramér's V shows the association is present but not especially strong. This test cannot explain why the difference exists, or establish that product type causes it.

## Did changing the time period change the result?

We compared all of 2019 with January–October 2019. The largest change in any product's reported-relief rate was 0.25 percentage points. This suggests the main product comparisons are similar in these two periods. It does not mean the full dataset has no reporting gaps.

## Did the company comparison hold up?

We independently calculated the product-aware company comparison in Python and checked it against the SQL results. All 61 qualifying companies matched on complaint counts and reported rates.

Requiring at least 20 peer complaints for every product still left 61 companies in the full-year comparison. For the three companies with the largest labeled complaint counts, the adjusted differences shifted by at most 0.49 percentage points when using January–October.

The comparison is fairly stable across these checks, but it still accounts only for product mix, not the exact complaint issues. Different companies are compared against different peer groups. The gaps should guide further investigation, not a company ranking.

## What this means

Product and company response patterns differ in this historical sample. The biggest question for the next stage is whether the written complaint text helps us understand differences that product and issue categories do not capture.

The data contains only published narratives. Reported relief is a company response category, not a measure of customer satisfaction.
