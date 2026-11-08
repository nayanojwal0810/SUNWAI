# Complaint Dataset Data Dictionary

This document explains the 18 columns in the historical Consumer Financial Protection Bureau (CFPB) complaints dataset (`complaints.csv.gz`). The dataset covers complaints received between January 1, 2019 and January 9, 2020.

| Column Name | Description | Data Type | Missing | Project Role |
| :--- | :--- | :--- | :---: | :--- |
| `date_received` | Date the CFPB received the complaint | Date (`YYYY-MM-DD`) | 0.00% | Timeline tracking and monthly trends |
| `product` | Main financial product or service | Categorical text | 0.00% | Primary grouping category |
| `sub_product` | Specific product type | Categorical text | 0.00% | Detailed product filtering |
| `issue` | High-level problem chosen from a predefined menu | Categorical text | 0.00% | Problem categorization |
| `sub_issue` | Specific secondary problem chosen from a menu | Categorical text | 13.45% | Granular problem analysis |
| `consumer_complaint_narrative` | Customer's written complaint description | Text | 0.00% | NLP analysis and text feature modeling |
| `company_public_response` | Optional public statement from the company | Categorical text | 47.91% | Public response pattern analysis |
| `company` | Legal name of the financial company | Categorical text | 0.00% | Company-level complaint volume comparisons |
| `state` | Consumer's state or territory postal code | Categorical text | 0.44% | Geographic distribution |
| `zip_code` | First three digits of consumer's ZIP code | Masked text (`XX`) | 22.35% | Regional location analysis |
| `tags` | Optional demographic segment indicators | Categorical text | 83.18% | Segment analysis (older Americans, servicemembers) |
| `consumer_consent_provided` | Confirmation that consumer agreed to share text | Categorical text | 0.00% | Verification indicator (constant across dataset) |
| `submitted_via` | Intake submission channel | Categorical text | 0.00% | Intake channel (all `Web` in this extract) |
| `date_sent_to_company` | Date the CFPB forwarded complaint to company | Date (`YYYY-MM-DD`) | 0.00% | Latency calculation (`sent` minus `received`) |
| `company_response_to_consumer` | Formal resolution outcome reported by company | Categorical text | 0.00% | Target label mapping for relief classification |
| `timely_response` | Whether the company responded on time | Categorical text (`Yes`/`No`) | 0.00% | Timeliness metric (post-intake outcome) |
| `consumer_disputed` | Historical flag for consumer dispute of outcome | Float / Boolean | 100.00% | Not usable (CFPB discontinued field in 2017) |
| `complaint_id` | Unique identifier assigned to each complaint | Integer | 0.00% | Primary key and table joins |

## Important Notes

- **Written complaints versus structured issue categories:** The `issue` field comes from a fixed dropdown list selected during submission. The `consumer_complaint_narrative` contains the customer's actual words, which provide context that dropdown categories cannot capture.
- **Company responses do not prove customer satisfaction:** The `company_response_to_consumer` field records what the institution reported to close the complaint (such as `Closed with explanation`). It does not indicate whether the customer was satisfied with that outcome.
- **Published narratives only:** All 117,214 records in this historical extract contain a non-empty customer narrative. Nationwide CFPB data includes many complaints without written text; this specific extract focuses on complaints where consumers opted into public sharing.
- **Fields with no usable information:** The `consumer_disputed` field is completely empty because the CFPB stopped collecting dispute data in early 2017. Columns like `submitted_via` and `consumer_consent_provided` have only one value across the entire file.
