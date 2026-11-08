# Raw Dataset Profile — Consumer Financial Protection Bureau Complaints

## 1. Dataset Source and File Information

- **Dataset Name:** Historical CFPB Consumer Complaints
- **Relative Path:** `data/raw/complaints.csv.gz`
- **File Size:** 47,322,719 bytes (~45.13 MB compressed)
- **SHA-256 Checksum:** `f4a5e174d364f1e1a25fac324e1a8224ff4e9454326e6e58abaa194bca93097b`
- **Checksum Verified:** Yes
- **Valid Gzip Format:** Yes
- **Original Source Agency:** US Consumer Financial Protection Bureau (CFPB)
- **Historical Distribution:** SMLTAR distribution by Emil Hvitfeldt and Julia Silge

## 2. Dataset Structure and Schema

- **Total Rows:** 117,214
- **Total Columns:** 18

| Column Name | Inferred Data Type | Missing Count | Missing Percentage |
| :--- | :--- | :---: | :---: |
| `date_received` | `object` | 0 | 0.00% |
| `product` | `object` | 0 | 0.00% |
| `sub_product` | `object` | 0 | 0.00% |
| `issue` | `object` | 0 | 0.00% |
| `sub_issue` | `object` | 15,764 | 13.45% |
| `consumer_complaint_narrative` | `object` | 0 | 0.00% |
| `company_public_response` | `object` | 56,156 | 47.91% |
| `company` | `object` | 0 | 0.00% |
| `state` | `object` | 514 | 0.44% |
| `zip_code` | `object` | 26,196 | 22.35% |
| `tags` | `object` | 97,503 | 83.18% |
| `consumer_consent_provided` | `object` | 0 | 0.00% |
| `submitted_via` | `object` | 0 | 0.00% |
| `date_sent_to_company` | `object` | 0 | 0.00% |
| `company_response_to_consumer` | `object` | 0 | 0.00% |
| `timely_response` | `object` | 0 | 0.00% |
| `consumer_disputed` | `float64` | 117,214 | 100.00% |
| `complaint_id` | `int64` | 0 | 0.00% |

## 3. Record Integrity and Identifier Uniqueness

- **Identifier Column:** `complaint_id`
- **Missing Identifiers:** 0
- **Distinct Identifiers:** 117,214
- **Duplicate Identifiers:** 0
- **Integrity Assessment:** Every record has a valid, non-null, unique complaint identifier.

## 4. Consumer Complaint Narrative Statistics

- **Total Records:** 117,214
- **Missing Narratives:** 0
- **Blank/Whitespace-only Narratives:** 0
- **Nonempty Narratives:** 117,214 (100.00%)
- **Distinct Narrative Texts:** 106,360
- **Repeated Narrative Text Groups:** 4,911 unique strings appearing multiple times
- **Total Records with Repeated Narratives:** 15,765 (13.45% of dataset)
- **Minimum Character Length:** 11 characters
- **Median Character Length:** 676.0 characters
- **Maximum Character Length:** 32,317 characters
- **Narratives with Redaction Placeholders (`XXXX`):** 91,595 (78.14%)

## 5. Temporal Range and Date Quality

| Date Field | Earliest Date | Latest Date | Missing Count | Invalid Values |
| :--- | :---: | :---: | :---: | :---: |
| `date_received` | 2019-01-01 | 2020-01-09 | 0 | 0 |
| `date_sent_to_company` | 2019-01-01 | 2020-01-09 | 0 | 0 |

## 6. Financial Product Distribution

| Product Category | Record Count | Percentage |
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

## 7. Company Response to Consumer Distribution

| Company Response Category | Record Count | Percentage |
| :--- | :---: | :---: |
| Closed with explanation | 94,941 | 81.00% |
| Closed with non-monetary relief | 16,437 | 14.02% |
| Closed with monetary relief | 5,118 | 4.37% |
| Untimely response | 718 | 0.61% |

## 8. Operational and Intake Attributes

- **Distinct Financial Institutions/Companies:** 2,541
- **Distinct States/Territories Represented:** 58

### Top 10 Companies by Complaint Volume

| Company Name | Complaint Count | Percentage |
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

### Submission Channel (`submitted_via`)

| Channel | Count | Percentage |
| :--- | :---: | :---: |
| Web | 117,214 | 100.00% |

### Timely Response (`timely_response`)

| Timely Response Flag | Count | Percentage |
| :--- | :---: | :---: |
| Yes | 115,136 | 98.23% |
| No | 2,078 | 1.77% |

### Demographic Tags (`tags`)

| Tag Segment | Count | Percentage |
| :--- | :---: | :---: |
| [Missing] | 97,503 | 83.18% |
| Servicemember | 13,415 | 11.44% |
| Older American | 4,593 | 3.92% |
| Older American, Servicemember | 1,703 | 1.45% |

## 9. Important Data Quality Findings

1. **Complete Narrative Coverage (100%):** Every single record contains a valid consumer complaint narrative. This confirms the dataset is a pre-filtered historical extract curated specifically for text analysis.
2. **Single Intake Channel and Uniform Consent:** 100% of complaints were submitted via `Web` and have `Consent provided` recorded. This indicates narrative availability is coupled with online submission and consumer opt-in.
3. **Complete Missingness of `consumer_disputed` (100% NaN):** The consumer dispute flag is entirely empty across all 117,214 records because the CFPB discontinued collecting this field in early 2017, prior to this dataset's 2019–2020 window.
4. **Repeated Text Clusters (13.45% of Records):** There are 4,911 unique narrative texts that appear more than once, accounting for 15,765 total records. These represent credit repair boilerplate templates or batch submissions and must be handled during train/validation/test splitting to prevent data leakage.
5. **High Concentration in Credit Reporting:** Three nationwide credit reporting agencies (TransUnion, Equifax, and Experian) account for 37.65% of all complaints, and the Credit Reporting product category represents 47.40% of the dataset.

## 10. Data Limitations and Cleaning Recommendations

- **Outcome Target Definition:** Because `consumer_disputed` is completely missing, the prediction target for decision support must be derived from `company_response_to_consumer` (e.g., relief vs. explanation).
- **Leakage Prevention:** Post-intake attributes (`date_sent_to_company`, `company_response_to_consumer`, `timely_response`, `company_public_response`) must not be used as features for complaint intake classification models.
- **Template De-duplication:** Repeated narratives must be grouped or stratified carefully so that copies of boilerplate templates do not cross training and evaluation splits.
- **Partial Month at Extract End:** The dataset terminates on January 9, 2020 (only 535 records for January 2020 compared to ~10,000/month in 2019). Temporal trend analyses should establish a clean 2019 full-calendar-year observation window.
