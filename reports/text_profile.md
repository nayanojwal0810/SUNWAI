# Complaint Narrative Quality and Profiling Report

## 1. Text Dataset Overview

This report profiles the customer-written complaint narratives in the prepared SUNWAI dataset. The analytical scope covers the full historical extract of 117,214 complaints (January 1, 2019 through January 9, 2020), which differs from the calendar-year-2019 business analysis window. Every record in this extract contains an original narrative submitted online with consumer consent.

- **Total complaint records:** 117,214
- **Nonempty processed narratives (`text_nlp`):** 117,210 (99.997%)
- **Empty processed narratives:** 4 (records where narratives consisted exclusively of masking placeholders and whitespace)
- **Masking placeholder rate:** 78.01% of narratives (91,434 records)

### Text Processing Method

The prepared text field (`text_nlp`) is an analytical copy derived from `consumer_complaint_narrative` using lightweight standard transformations:

1. **Lowercase conversion:** Standardized using lowercase transformation.
2. **Whitespace normalization:** Line breaks, tabs, and repeated spaces collapsed to single spaces.
3. **Masking placeholder removal:** CFPB redaction strings consisting of runs of four or more `X` characters not immediately adjacent to alphabetic letters were removed from `text_nlp` to avoid artificial high-frequency terms.
4. **Trimming:** Leading and trailing whitespace removed.

Normal punctuation, negation words (e.g., 'not', 'never', 'did not'), financial numbers, and domain vocabulary were strictly preserved to retain semantic context for future NLP tasks.

## 2. Narrative Quality

Narratives exhibit substantial variation in length, ranging from brief notices to multi-page dispute descriptions. Word counts are calculated using a consistent regex token-counting rule (`\b\w+\b`).

| Metric | Value |
| :--- | :---: |
| Median character count | 641 characters |
| Median word count | 116 words |
| 10th percentile word count | 31 words |
| 90th percentile word count | 393 words |
| Short narratives (< 20 words) | 5,938 (5.07%) |
| Masked narratives (containing `XXXX`) | 91,434 (78.01%) |

The median complaint contains 116 words, while the middle 80% spans from 31 to 393 words. Complaints with fewer than 20 words account for 5.07% of all narratives, indicating that most records contain multi-sentence descriptions.

## 3. Repeated Narratives

Using the stable `narrative_group_id` (derived from lowercased, whitespace-collapsed original narratives), repeated complaint texts were analyzed across the historical extract:

| Metric | Value |
| :--- | :---: |
| Distinct narrative groups | 104,196 |
| Groups appearing more than once | 6,051 |
| Complaints belonging to repeated groups | 19,069 |
| Share of complaints in repeated groups | 16.27% |
| Largest group size | 442 complaints |

Across the historical extract, 94.19% of distinct narrative groups appear exactly once, while repeated groups account for 16.27% of all complaint records. Because consumers or submitting representatives sometimes submit identical narrative text for separate filings, these identical records are preserved in full. However, identical narratives across multiple records require group-aware partitioning in downstream modeling.

## 4. Differences Across Products

Text characteristics differ substantially across financial product lines:

| Financial Product | Complaints | Median Words | Masking Rate | Repeated Narrative % |
| :--- | :---: | :---: | :---: | :---: |
| Credit reporting, credit repair services, or other personal consumer reports | 55,558 | 86 | 75.82% | 30.64% |
| Debt collection | 22,287 | 111 | 75.64% | 7.49% |
| Credit card or prepaid card | 11,571 | 172 | 79.60% | 2.01% |
| Mortgage | 9,449 | 218 | 86.77% | 0.28% |
| Checking or savings account | 6,915 | 178 | 82.92% | 0.36% |
| Student loan | 3,941 | 173 | 79.52% | 0.30% |
| Vehicle loan or lease | 2,713 | 174 | 81.46% | 1.25% |
| Money transfer, virtual currency, or money service | 2,563 | 163 | 87.16% | 0.78% |
| Payday loan, title loan, or personal loan | 2,217 | 142 | 77.94% | 1.26% |

### Observations

- **Text length disparity:** Median length varies across products, ranging from 86 words in Credit reporting, credit repair services, or other personal consumer reports to 218 words in Mortgage.
- **Repetition concentration:** Repeated narrative shares differ markedly by product, peaking at 30.64% in Credit reporting, credit repair services, or other personal consumer reports compared to 0.28% in Mortgage. The high repetition rate in credit-reporting complaints suggests that repeated or template-like wording may influence topic discovery.
- **Placeholder prevalence:** Masking placeholders are widespread across all product categories, with rates ranging from 75.64% in Debt collection to 87.16% in Money transfer, virtual currency, or money service.

## 5. Implications for NLP and Modeling

The narrative profile establishes critical methodological boundaries for subsequent NLP and machine learning stages:

1. **Group-aware data partitioning:** Because 16.27% of complaints belong to repeated narrative groups, naive random train/test splitting would leak identical narratives across folds, inflating evaluation metrics. Splits must partition on `narrative_group_id`.
2. **Vocabulary fitting on training splits only:** TF-IDF vectorizers, topic models, and vocabulary selectors must be fitted strictly on training folds and transformed on validation/test folds without data leakage.
3. **Influence of repeated narratives on topic discovery:** Given the concentration of identical narratives in certain products, theme discovery should evaluate both the full dataset and unique-narrative subsets to observe how repeated wording affects extracted topics.
4. **Preservation of original narratives:** The original `consumer_complaint_narrative` remains available in the clean dataset, while `text_nlp` serves as a clean baseline representation for tokenization and vectorization.

## 6. Limitations

- **Selection bias:** The dataset represents only consumers who submitted narratives online and opted to make them public.
- **Masking artifacts:** Removing standalone `XXXX` placeholders removes redaction symbols but cannot reconstruct masked numbers, dates, or entity names.
- **Descriptive word metrics:** Word counts reflect regex-based token counts rather than syntactic or semantic complexity.
- **Observational scope:** Repeated narratives reflect shared text patterns, not verified consumer satisfaction or complaint validity.
