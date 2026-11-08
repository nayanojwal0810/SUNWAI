# SUNWAI — Dataset Data Dictionary

This document details the 18 columns in the historical Consumer Financial Protection Bureau (CFPB) complaints dataset (`data/raw/complaints.csv.gz`). The dataset represents a historical extract covering complaints received between January 1, 2019 and January 9, 2020.

## Overview Table

| Column Name | Meaning in Simple English | Expected Kind of Information | Missing Percentage | Planned Project Use |
| :--- | :--- | :--- | :---: | :--- |
| `date_received` | The date the CFPB received the complaint from the consumer. | ISO date string (`YYYY-MM-DD`). | 0.00% | Time-series trends, monthly complaint volume aggregation, and temporal cohort analysis. |
| `product` | The primary financial product or service category identified in the complaint. | Predefined categorical string (e.g., `Debt collection`, `Mortgage`). | 0.00% | Primary dimensional breakdown, SQL slice-and-dice, product-mix adjustments, and model stratification. |
| `sub_product` | The specific sub-category of the financial product. | Predefined categorical string (e.g., `Credit card`, `Conventional fixed mortgage`). | 0.00% | Granular product analysis and drill-down reporting in SQL and dashboards. |
| `issue` | The high-level issue or problem selected by the consumer from a standard list. | Predefined categorical text (e.g., `Attempts to collect debt not owed`). | 0.00% | Structured problem categorization and comparison against NLP-derived themes. |
| `sub_issue` | The detailed secondary issue selected by the consumer. | Granular categorical text (e.g., `Debt is not yours`). | 13.45% | In-depth operational dispute drill-down where present. |
| `consumer_complaint_narrative` | The consumer's written description of the incident, with personal identifiers redacted. | Free-form unstructured text string. | 0.00% | Natural language processing, TF-IDF vectorization, topic modeling, and narrative feature extraction. |
| `company_public_response` | The optional public response selected by the company from a predefined CFPB menu. | Predefined categorical statement. | 47.91% | Descriptive analysis of corporate public communication strategies. |
| `company` | The legal commercial entity against which the complaint was filed. | Organization name string (e.g., `TRANSUNION INTERMEDIATE HOLDINGS, INC.`). | 0.00% | Entity-level volume benchmarking and company relief rate comparisons. |
| `state` | The US state or territory of the consumer's mailing address. | Two-letter postal abbreviation (e.g., `CA`, `FL`, `TX`). | 0.44% | Regional complaint distribution and geographic pattern analysis. |
| `zip_code` | The three-digit zip code prefix of the consumer, with remaining digits redacted. | Five-character string ending in `XX` (e.g., `335XX`). | 22.35% | High-level regional clustering where available. |
| `tags` | Flags denoting special consumer demographic populations. | Categorical identifier (e.g., `Servicemember`, `Older American`). | 83.18% | Protected and vulnerable demographic segment analysis. |
| `consumer_consent_provided` | Confirmation that the consumer agreed to publish their written narrative. | Categorical string (`Consent provided`). | 0.00% | Dataset verification indicator (constant across this narrative-only extract). |
| `submitted_via` | The intake channel through which the complaint was submitted to the CFPB. | Categorical channel name (`Web`). | 0.00% | Intake channel distribution (constant across this narrative-only extract). |
| `date_sent_to_company` | The date the CFPB forwarded the complaint to the financial company for review. | ISO date string (`YYYY-MM-DD`). | 0.00% | Operational agency routing latency calculation (`date_sent_to_company` minus `date_received`). |
| `company_response_to_consumer` | The formal resolution outcome reported by the financial institution to the CFPB. | Predefined categorical outcome (e.g., `Closed with explanation`). | 0.00% | Target label mapping for machine learning classification (relief versus explanation). |
| `timely_response` | Whether the company responded within the statutory CFPB deadline (typically 15 days). | Binary indicator string (`Yes` or `No`). | 0.00% | Regulatory compliance monitoring; excluded from intake predictive models. |
| `consumer_disputed` | Historical flag showing whether the consumer disputed the company's response. | Deprecated boolean / float indicator. | 100.00% | Not usable for analysis. Discontinued by CFPB in early 2017; completely empty in this dataset. |
| `complaint_id` | Unique sequential numeric identifier assigned by the CFPB to each complaint. | 6- to 7-digit positive integer. | 0.00% | Relational primary key, table joins, deduplication, and record auditing. |

---

## Important Conceptual Distinctions

Understanding the following conceptual differences is essential for correct data modeling, analysis, and interpretation:

### 1. Complaint Narrative vs. Structured Issue Category
- **`issue` and `sub_issue`** are chosen by the consumer from a fixed, standardized menu when submitting the complaint form. They provide consistent, predefined buckets across all consumers but lack situational nuances.
- **`consumer_complaint_narrative`** is the consumer's unstructured, free-form written narrative. It reveals root causes, emotional distress, specific sequence of events, and nuances not captured in rigid drop-down menus.
- **Analytical Implication:** A central goal of SUNWAI is evaluating whether unstructured narratives provide actionable intelligence beyond structured issue categories.

### 2. Date Received vs. Date Sent to Company
- **`date_received`** is the timestamp when the consumer formally lodged the complaint with the CFPB. This is the true intake date.
- **`date_sent_to_company`** is the date when CFPB review finished and the complaint was transmitted to the financial institution.
- **Analytical Implication:** The difference represents CFPB intake processing latency. Crucially, `date_sent_to_company` is an operational milestone that occurs after intake, so it should not be treated as a consumer intake feature.

### 3. Company Response vs. Verified Customer Satisfaction
- **`company_response_to_consumer`** reflects the outcome category *reported by the financial institution* (e.g., `Closed with monetary relief`, `Closed with explanation`).
- A status of `Closed with explanation` indicates only that the firm submitted an explanation to close the CFPB case; it does *not* imply that the consumer agreed with the explanation, felt fairly treated, or had their grievance resolved.
- **Analytical Implication:** Business metrics and classification models evaluate *reported company relief*, not consumer satisfaction or institutional guilt.

### 4. Missing Narrative vs. Empty Complaint Record
- In the broader nationwide CFPB database, only approximately 30% to 40% of complaints contain a published narrative because publication requires explicit consumer opt-in (`Consent provided`) and redaction processing.
- In this specific historical research extract (`complaints.csv.gz`), **100% of records have non-empty narratives**.
- **Analytical Implication:** This dataset is already pre-filtered for text-analytic tasks. Conclusions drawn from this sample reflect consumers who chose to write detailed public complaints, rather than the complete volume of all financial disputes.

### 5. Intake Features vs. Post-Intake Operational Outcomes
- **Intake Features (Available at complaint submission):** `date_received`, `product`, `sub_product`, `issue`, `sub_issue`, `consumer_complaint_narrative`, `company`, `state`, `zip_code`, `tags`, `submitted_via`.
- **Post-Intake Attributes (Occurring after submission):** `date_sent_to_company`, `company_response_to_consumer`, `timely_response`, `company_public_response`.
- **Analytical Implication:** Post-intake attributes must never be used as inputs in predictive intake models to prevent data leakage.

