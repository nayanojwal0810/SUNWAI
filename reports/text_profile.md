# Complaint text findings

## What we analyzed

We examined the written narratives in all 117,214 complaints, including the partial January 2020 period. This differs from the 2019-only business analysis.

We made a separate text copy for analysis. It uses lowercase letters, removes repeated spaces, and removes XXXX-style masking markers when they are not part of ordinary words. The original narrative remains in the cleaned file.

## How much text is available?

| Measure | Result |
| --- | ---: |
| Narratives with text after processing | 117,210 |
| Narratives empty after processing | 4 |
| Median length | 116 words |
| 10th to 90th percentile | 31–393 words |
| Narratives shorter than 20 words | 5,938 (5.07%) |
| Narratives containing masking markers | 91,434 (78.01%) |

Most complaints contain more than a short sentence, but their length and wording vary widely. Longer text does not necessarily describe a more serious problem.

## How often does text repeat?

| Measure | Result |
| --- | ---: |
| Different normalized narrative groups | 104,196 |
| Groups used by more than one complaint | 6,051 |
| Complaints in those repeated groups | 19,069 (16.27%) |
| Largest repeated group | 442 complaints |

Repeated wording is particularly common in credit reporting: 30.64% of those complaints belong to repeated groups. The corresponding share for mortgage complaints is 0.28%.

This tells us repetition may affect which themes a text model finds. It does not tell us who wrote the complaints or why the wording matches.

## Differences in text length

Mortgage complaints have the longest median narrative among the products in this extract, at 218 words. Credit reporting complaints have the shortest median, at 86 words.

Masking markers are common across products. The highest measured rate is 87.16% in money transfer complaints.

## What needs care later?

We should compare theme results with and without counting repeated narratives more than once. For predictive models, matching narratives must be kept in the same training, validation, or test group. Text vocabularies must be learned from training data only.

The text-processing step does not identify topics or sentiment. Those analyses have not been completed.
