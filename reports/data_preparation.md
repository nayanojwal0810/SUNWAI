# Complaint Dataset Preparation

## 1. Dataset Preparation

- **Source dataset:** `data/raw/complaints.csv.gz`
- **Cleaned dataset:** `data/processed/complaints_clean.csv.gz`
- **Input records:** 117,214
- **Cleaned records:** 117,214
- **Input columns:** 18
- **Cleaned columns:** 19

## 2. Changes Applied

- **Removed empty column:** `consumer_disputed` was verified to be 100.00% missing (all 117,214 values empty) and removed from the analytical dataset.
- **Standardized identifiers:** Confirmed `complaint_id` contains zero missing and zero duplicate values; stored as standard integer primary key.
- **Standardized dates:** Parsed `date_received` and `date_sent_to_company` into `YYYY-MM-DD` format with zero invalid or missing values.
- **Cleaned whitespace:** Trimmed leading and trailing whitespace from string and categorical columns without modifying text casing, wording, or redactions.
- **Derived reported relief (`reported_relief`):** Created a binary outcome target from `company_response_to_consumer`:
  - `1` (Relief): 21,555 records (monetary or non-monetary relief).
  - `0` (No relief): 94,941 records (closed with explanation).
  - `<NA>` (Untimely / Unlabeled): 718 records.
- **Derived narrative grouping (`narrative_group_id`):** Generated a stable SHA-256 hash from normalized narrative text (whitespace collapsed, lowercased) to group identical complaint submissions for evaluation splits.

| Field | Transformation | Result |
| :--- | :--- | :--- |
| `consumer_disputed` | Removed | Dropped entirely empty column |
| `reported_relief` | Derived binary outcome | 21,555 relief (1), 94,941 no-relief (0), 718 unlabeled (NA) |
| `narrative_group_id` | Derived grouping hash | 104,196 distinct groups; 19,069 records share a group |
| Categorical / Text | Trimmed whitespace | Preserved original values, casings, and missing indicators |
| Dates | Standardized format | Parsed YYYY-MM-DD; 0 missing, 0 invalid |

## 3. Data Integrity and Verification

- **Record preservation:** All 117,214 input complaint records were verified and preserved in the cleaned dataset without dropping rows.
- **Identifier consistency:** All complaint IDs were validated against the source dataset for complete uniqueness and absence of null values.
- **Category consistency:** Full distributions of financial products and company responses were confirmed to match the original raw dataset exactly.
- **Outcome mapping:** Derived outcomes were independently verified against source response categories (21,555 relief, 94,941 explanation, 718 untimely).
- **Narrative preservation:** Customer narrative text was preserved with original casing and redactions intact, while generating 104,196 distinct narrative group hashes to support group-aware modeling splits.
- **Reload verification:** The exported compressed CSV was reloaded from disk and re-verified for schema integrity, row count, outcome labels, and text fields.

## 4. Important Notes

- **Outcome label availability:** Only closed responses with known relief outcomes are labeled with `1` or `0`. Untimely responses remain unlabeled (`<NA>`) and will be excluded from supervised model training while remaining available for exploratory SQL and dashboard metrics.
- **Grouping usage:** The `narrative_group_id` column is intended strictly for grouping data during train/validation/test splits. It is not an input feature for predictive models.
- **Repeated narrative share:** 19,069 records (16.27% of the dataset) share identical normalized narrative text with at least one other record, underscoring the importance of grouped cross-validation.
- **Preserved narrative text:** The original verbatim complaint narratives are preserved without lowercasing, stopword removal, or tokenization. Text preprocessing will occur during dedicated NLP tasks.
- **Temporal coverage:** The cleaned dataset retains all records through January 9, 2020. Filtering to complete monthly or annual periods will be performed during time-series analysis.
