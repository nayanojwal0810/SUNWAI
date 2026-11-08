# Data overview

## What we have

The historical file contains 117,214 US consumer complaints received from January 1, 2019 to January 9, 2020. It has 18 columns, nine product categories, and 2,541 company names.

Every complaint in this extract includes a written narrative. This is a subset of published CFPB complaints, not the full complaint database.

## What we found

| Measure | Result |
| --- | ---: |
| Credit reporting complaints | 55,558 (47.40%) |
| Debt collection complaints | 22,287 (19.01%) |
| Complaints closed with an explanation | 94,941 (81.00%) |
| Complaints with reported monetary or non-monetary relief | 21,555 (18.39%) |
| Untimely responses | 718 (0.61%) |

Credit reporting and debt collection make up roughly two-thirds of this extract. The results tell us where this sample is concentrated, but complaint counts alone do not show how common problems are among a company's customers.

## Data quality

| Check | Result |
| --- | --- |
| Missing or repeated complaint IDs | None |
| Missing complaint narratives | None |
| consumer_disputed | Empty in every row |
| tags | Missing in 83.18% of rows |
| company_public_response | Missing in 47.91% of rows |
| zip_code | Missing in 22.35% of rows |

Some complaints have exactly the same written narrative: 15,765 rows belong to groups with identical raw text. After ignoring case and differences in spacing, 19,069 rows belong to repeated-text groups. We keep these complaints, but later model evaluation must not place matching narratives in both training and test data.

## Limits

January 2020 covers only nine days. We therefore use 2019 for the business analysis. The dataset includes only publicly shared narratives, and company response categories do not tell us whether consumers were satisfied.
