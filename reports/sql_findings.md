# SQL findings

## What we analyzed

The SQL analysis uses complaints received during 2019, excluding the partial January 2020 period.

- Total complaints: 116,679
- Complaints with a known relief label: 115,961
- Complaints without a relief label: 718
- Overall reported-relief rate among labeled complaints: 18.55%

The SQLite database has a complaint table connected to product, company, and state tables. Eight SQL queries produce the summaries used here.

## Which products appear most?

| Product | Complaints in 2019 | Reported-relief rate |
| --- | ---: | ---: |
| Credit reporting | 55,175 | 21.66% |
| Debt collection | 22,209 | 11.51% |
| Credit card or prepaid card | 11,553 | 28.16% |
| Mortgage | 9,427 | 6.43% |
| Checking or savings account | 6,896 | 28.36% |

Credit reporting makes up 47.29% of the 2019 sample. Relief rates also differ by product. For example, the share of labeled complaints with reported relief is higher for checking and savings accounts than for mortgages. This does not mean one product causes a better outcome.

## How were companies compared?

The three companies with the most complaints account for 37.52% of all 2019 records. But a count is not a complaint rate per customer, so it cannot be used on its own to judge service quality.

We also compared company-reported relief with an expected rate based on the products each company handles. For each product, the comparison uses other companies' cases, not the company's own cases.

There are 61 companies with at least 200 labeled complaints and a usable peer comparison for every product they handle. Their observed-minus-expected differences range from -23.38 to +29.56 percentage points.

These gaps show differences worth examining. They do not prove which companies handle complaints better, because the comparison does not account for the exact issues, complaint details, or differences in reporting practices.

## Other observations

Companies marked 98.22% of 2019 complaints as receiving a timely response. This is separate from whether relief was reported.

The extract has much fewer complaints in November and December than earlier months. Reporting delays or the source snapshot may play a part. We cannot infer a market-wide decline from these counts.

The SQL files are in sql/analysis/, and the detailed result tables are saved locally in outputs/sql/.
