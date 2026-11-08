# Complaint Dataset Profile

### Dataset Overview

- **Total records:** 117,214
- **Total fields:** 18
- **Financial products:** 9
- **Financial companies:** 2,541

### Data Quality

| Field / Check | Metric | Description |
| :--- | :---: | :--- |
| `complaint_id` uniqueness | 0 duplicates | Every record has a unique identifier with 0 missing |
| Narrative presence | 100.00% | All 117,214 records include non-empty narrative text |
| Repeated narratives | 15,765 records | 4,911 unique narrative texts appear multiple times |
| Date fields | 0 missing | Both received and sent dates are completely populated |
| `consumer_disputed` | 100.00% missing | Field is entirely empty across all records |
| `tags` | 83.18% missing | Optional demographic segment indicators |
| `company_public_response` | 47.91% missing | Optional public statement from company |
| `zip_code` | 22.35% missing | Partially masked or omitted location data |

### Complaint Distribution

#### Financial Products

| Product Category | Complaints | Share |
| :--- | :---: | :---: |
| Credit reporting, credit repair services, or other personal consumer reports | 55,558 | 47.40% |
| Debt collection | 22,287 | 19.01% |
| Credit card or prepaid card | 11,571 | 9.87% |
| Mortgage | 9,449 | 8.06% |
| Checking or savings account | 6,915 | 5.90% |
| Student loan | 3,941 | 3.36% |
| Vehicle loan or lease | 2,713 | 2.31% |
| Money transfer, virtual currency, or money service | 2,563 | 2.19% |
| Payday loan, title loan, or personal loan | 2,217 | 1.89% |

#### Company Responses

| Company Response Category | Complaints | Share |
| :--- | :---: | :---: |
| Closed with explanation | 94,941 | 81.00% |
| Closed with non-monetary relief | 16,437 | 14.02% |
| Closed with monetary relief | 5,118 | 4.37% |
| Untimely response | 718 | 0.61% |

#### Top 10 Companies by Complaint Volume

| Company | Complaints | Share |
| :--- | :---: | :---: |
| TRANSUNION INTERMEDIATE HOLDINGS, INC. | 15,237 | 13.00% |
| EQUIFAX, INC. | 14,607 | 12.46% |
| Experian Information Solutions Inc. | 14,290 | 12.19% |
| CITIBANK, N.A. | 3,359 | 2.87% |
| CAPITAL ONE FINANCIAL CORPORATION | 3,281 | 2.80% |
| JPMORGAN CHASE & CO. | 3,104 | 2.65% |
| BANK OF AMERICA, NATIONAL ASSOCIATION | 2,830 | 2.41% |
| WELLS FARGO & COMPANY | 2,821 | 2.41% |
| SYNCHRONY FINANCIAL | 2,372 | 2.02% |
| Navient Solutions, LLC. | 2,057 | 1.75% |

### Key Findings

1. **Full narrative coverage:** All 117,214 complaints include customer-written narratives submitted online with publication consent.
2. **Heavy credit reporting volume:** Credit reporting represents 47.40% of complaints, followed by debt collection at 19.01%.
3. **Company concentration:** Three nationwide credit reporting agencies (TransUnion, Equifax, Experian) account for 37.65% of all complaints.
4. **Response outcomes:** Most complaints (81.00%) were closed with an explanation, while monetary or non-monetary relief was reported in 18.39% of cases.
5. **Repeated texts:** There are 4,911 unique narrative texts that appear multiple times, covering 15,765 records (13.45% of the dataset).

### Limitations

- **Historical extract:** The data spans January 1, 2019 to January 9, 2020. January 2020 contains only 535 records and does not represent a full month.
- **Narrative-only sample:** Records include only consumers who opted to publish written narratives, which is a subset of all CFPB complaints.
- **Unpopulated dispute field:** The `consumer_disputed` column contains no data and cannot be used for analysis or outcome modeling.
- **Repeated text:** Identical complaints should be grouped or handled during dataset splitting to avoid evaluating models on duplicate texts.
- **Self-reported outcomes:** Company responses reflect categories reported by institutions rather than independently verified consumer satisfaction.
