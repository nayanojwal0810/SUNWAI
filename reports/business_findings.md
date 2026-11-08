# Business Analysis Findings

## Business Analysis Overview

This business analysis examines historical CFPB consumer complaints received during calendar year 2019 (January 1, 2019 through December 31, 2019). The analysis evaluates whether observed differences in reported relief rates across financial products and institutions reflect meaningful operational patterns, examines sampling uncertainty through confidence intervals, and tests the stability of findings across alternative observation windows.

- **Qualifying 2019 eligible complaints:** 115,961 records (excluding untimely responses without definitive outcome labels).
- **Overall reported-relief count:** 21,510 complaints (18.55% baseline relief rate).
- **Outcome definition:** Reported relief indicates monetary or non-monetary relief reported by the company to the CFPB; it does not measure customer satisfaction or complaint merit.

## Product Differences

Reported-relief rates vary significantly by product category. High-volume lending and collection products report consistently lower relief frequencies than transaction and depository accounts. Because product sample sizes range from 2,174 to 55,047 complaints, 95% Wilson score confidence intervals are calculated to assess precision.

| Product | Eligible Complaints | Reported Relief | Relief Rate | 95% Wilson CI | CI Width |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Credit reporting, credit repair services, or other personal consumer reports | 55,047 | 11,922 | 21.66% | [21.32%, 22.00%] | 0.68 pp |
| Debt collection | 21,824 | 2,513 | 11.51% | [11.10%, 11.95%] | 0.85 pp |
| Credit card or prepaid card | 11,533 | 3,248 | 28.16% | [27.35%, 28.99%] | 1.64 pp |
| Mortgage | 9,389 | 604 | 6.43% | [5.95%, 6.95%] | 1.00 pp |
| Checking or savings account | 6,884 | 1,952 | 28.36% | [27.30%, 29.43%] | 2.13 pp |
| Student loan | 3,881 | 357 | 9.20% | [8.33%, 10.15%] | 1.82 pp |
| Vehicle loan or lease | 2,681 | 286 | 10.67% | [9.55%, 11.89%] | 2.34 pp |
| Money transfer, virtual currency, or money service | 2,548 | 435 | 17.07% | [15.66%, 18.58%] | 2.92 pp |
| Payday loan, title loan, or personal loan | 2,174 | 193 | 8.88% | [7.75%, 10.15%] | 2.40 pp |

Estimated 95% Wilson confidence interval widths range from 0.68 percentage points (Credit reporting, credit repair services, or other personal consumer reports) to 2.92 percentage points (Money transfer, virtual currency, or money service). These intervals describe binomial sampling uncertainty under simplifying assumptions. Factors such as repeated narratives and selection into the published-narrative dataset may reduce the reliability of population-level uncertainty claims.

## Statistical Evidence

A chi-square test of independence was conducted on the contingency table of financial products versus complaint resolution outcomes (reported relief versus closed with explanation):

- **Chi-square statistic (χ²):** 3,595.8545
- **Degrees of freedom:** 8
- **P-value:** < 0.0001
- **Total observations analyzed:** 115,961
- **Cramér's V effect size:** 0.1761

### Interpretation

Under the test assumptions, the small p-value (< 0.0001) indicates an association where reported relief is not distributed uniformly across product categories. The chi-square test identifies an association under these assumptions, not causation. The Cramér's V of 0.1761 describes the strength of this observational association without proving practical business significance. Within this extract, observed product relief rates range from 6.43% for Mortgage to 28.36% for Checking or savings account.

### Reporting-Period Sensitivity

To evaluate whether the observed decline in complaint volume during late 2019 affects product-level findings, product relief rates for the full calendar year 2019 were compared against January through October 2019:

| Product | Full Year 2019 Eligible | Full Year Relief % | Jan–Oct 2019 Eligible | Jan–Oct Relief % | Difference (pp) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Debt collection | 21,824 | 11.51% | 19,885 | 11.76% | -0.25 |
| Checking or savings account | 6,884 | 28.36% | 6,200 | 28.61% | -0.25 |
| Money transfer, virtual currency, or money service | 2,548 | 17.07% | 2,380 | 16.85% | +0.22 |
| Credit card or prepaid card | 11,533 | 28.16% | 10,352 | 28.02% | +0.14 |
| Payday loan, title loan, or personal loan | 2,174 | 8.88% | 1,997 | 8.76% | +0.12 |
| Credit reporting, credit repair services, or other personal consumer reports | 55,047 | 21.66% | 48,911 | 21.75% | -0.09 |
| Mortgage | 9,389 | 6.43% | 8,460 | 6.48% | -0.05 |
| Vehicle loan or lease | 2,681 | 10.67% | 2,471 | 10.72% | -0.05 |
| Student loan | 3,881 | 9.20% | 3,682 | 9.15% | +0.05 |

The largest rate shift observed across all products was 0.25 percentage points (Debt collection: 11.51% full year vs. 11.76% Jan–Oct). Across all evaluated product categories, reported-relief rates shifted by at most 0.25 percentage points between the full year and the 10-month window. Small rate changes across reporting periods show stability within these two observation windows, but do not prove that reporting lags have no effect on broader complaint counts.

## Company Benchmark Robustness

SUNWAI's product-aware benchmark compares each company's observed relief rate to an expected rate based on peer-company rates across the specific product mix handled by that institution. An independent Python implementation was used to audit the SQL query and test benchmark robustness under stricter peer-support requirements and shorter observation windows.

### Benchmark Audit Results

- **Original SQL benchmark:** 61 qualifying companies (minimum 200 eligible complaints and at least 1 peer per product).
- **Independent Python replication:** 61 companies matched exactly across eligible complaint counts and rate metrics, with a maximum rate discrepancy of 0.0000 percentage points (within the 0.02 pp rounding threshold).
- **Stricter peer support (≥ 20 peers per product):** 61 of 61 companies retained (100.0% retention). All qualifying companies operate in products with substantial peer representation.
- **January–October window (≥ 20 peers):** 55 companies qualified under the 10-month threshold.

### Period Sensitivity for Top Three Companies by Volume

| Company | Full Year 2019 Complaints | Full Year Adjusted Diff (pp) | Jan–Oct 2019 Adjusted Diff (pp) | Shift (pp) |
| :--- | :---: | :---: | :---: | :---: |
| TRANSUNION INTERMEDIATE HOLDINGS, INC. | 14,923 | -23.38 | -23.19 | +0.19 |
| EQUIFAX, INC. | 14,607 | +4.83 | +4.77 | -0.06 |
| Experian Information Solutions Inc. | 14,245 | +29.56 | +29.07 | -0.49 |

Product-mix adjusted rate differences for the compared high-volume companies shifted by at most 0.49 percentage points between the full year and the 10-month window.

## Key Findings

1. **Product-level interval precision:** Estimated 95% Wilson confidence interval widths range from 0.68 percentage points for Credit reporting, credit repair services, or other personal consumer reports to 2.92 percentage points for Money transfer, virtual currency, or money service, reflecting sample size precision under binomial sampling assumptions.
2. **Product category outcome differences:** Chi-square testing (χ² = 3,595.8545, p < 0.0001, Cramér's V = 0.1761) indicates a statistically detectable association between product categories and reported resolution outcomes under test assumptions, with observed product relief rates ranging from 6.43% (Mortgage) to 28.36% (Checking or savings account).
3. **Stability across observation periods:** Product-level relief rates shifted by at most 0.25 percentage points when comparing the full calendar year against January through October 2019 (Debt collection: -0.25 pp shift).
4. **Replicated company benchmark:** The independent Python benchmark matched the SQL benchmark across all 61 qualifying companies (maximum rate discrepancy 0.0000 pp), with 100.0% of firms retained under stricter peer-support filtering (≥ 20 peers per product).
5. **Institution-level sensitivity:** Product-mix-adjusted differences for the highest-volume qualifying companies shifted by at most 0.49 percentage points across the two reporting periods. These descriptive comparisons reflect relative positioning against product peers rather than verified institutional service quality.

## Limitations

- **Observational self-reporting:** Relief metrics reflect company-submitted resolution codes, not verified consumer satisfaction or problem resolution.
- **Uncontrolled sub-issue mix:** The product-aware benchmark standardizes for high-level product mix but does not adjust for specific dispute sub-issues or account tenure.
- **Non-causal interpretation:** Differences in relief rates and benchmark gaps provide exploratory signals for investigation rather than proof of institutional service quality.
- **Narrative selection:** The analyzed records include only complaints with published narratives, which may overrepresent consumers willing to draft detailed written text.
