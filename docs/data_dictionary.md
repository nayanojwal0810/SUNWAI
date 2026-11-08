# Data dictionary

This page explains the fields used in SUNWAI. The source file contains 18 columns. The cleaned file keeps 17 of them and adds two new fields.

## Source complaint fields

| Field | Meaning |
| --- | --- |
| date_received | Date the CFPB received the complaint |
| product | Main type of financial product |
| sub_product | More specific product type |
| issue | Problem selected by the consumer |
| sub_issue | More detailed problem, when available |
| consumer_complaint_narrative | Written description of the complaint |
| company_public_response | Optional statement made public by the company |
| company | Company named in the complaint |
| state | State or territory code, when available |
| zip_code | Partly hidden ZIP code; stored as text |
| tags | Optional labels such as older consumer or servicemember |
| consumer_consent_provided | Whether publication consent was provided |
| submitted_via | How the complaint was submitted |
| date_sent_to_company | Date the complaint was sent to the company |
| company_response_to_consumer | Company's reported response category |
| timely_response | Whether the response was on time |
| consumer_disputed | Old dispute field; empty throughout this dataset |
| complaint_id | Unique number for a complaint |

Every record in this extract has a written narrative. The submission channel and consent fields have the same value in all records, so they are not useful for comparing groups.

## Fields added during cleaning

The file data/processed/complaints_clean.csv.gz contains 19 columns. It drops consumer_disputed because every value is missing, then adds:

| Field | Meaning |
| --- | --- |
| reported_relief | 1 for monetary or non-monetary relief; 0 for closed with explanation; empty for untimely response |
| narrative_group_id | Same value for narratives that match after lowercasing and whitespace normalization |

reported_relief describes the response category reported by the company. It is not a measure of consumer satisfaction.

narrative_group_id helps keep repeated text out of both the training and test sets. It must not be used as a prediction feature.

## Fields in the text file

The file data/processed/complaints_text.csv.gz has six columns:

| Field | Meaning |
| --- | --- |
| complaint_id | Complaint number used to match the cleaned file |
| narrative_group_id | Group for repeated narratives |
| text_nlp | Lowercased narrative with repeated spaces and masking markers removed |
| character_count | Number of characters in text_nlp |
| word_count | Number of word-like tokens in text_nlp |
| has_redaction | Whether the original text contained an XXXX-style masking marker |

text_nlp is a copy made for analysis. The original narrative is still in complaints_clean.csv.gz.

Both processed files are created locally and are not committed to GitHub.
