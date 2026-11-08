# Data cleaning

## What changed

We started with 117,214 complaints and kept every record. The source has 18 columns; the cleaned file has 19.

- Dates were put into YYYY-MM-DD format.
- Extra spaces around text fields were removed.
- Complaint IDs were checked for missing and repeated values.
- The empty consumer_disputed column was removed.
- Two fields were added: reported_relief and narrative_group_id.

The original complaint wording and letter case are kept apart from trimming spaces. The file is saved locally as data/processed/complaints_clean.csv.gz.

## How reported relief is defined

| Value | Company response | Records |
| --- | --- | ---: |
| 1 | Closed with monetary or non-monetary relief | 21,555 |
| 0 | Closed with explanation | 94,941 |
| Empty | Untimely response | 718 |

An empty label is not counted as no relief. These labels describe what a company reported, not whether its consumer was happy with the result.

## Why repeated text matters

Narratives were grouped using lowercased text with repeated spaces removed. This produced 104,196 distinct groups. Of these, 6,051 groups contain more than one complaint, covering 19,069 records (16.27%).

We did not delete those records. The group field will be used to prevent repeated narratives from appearing in both training and test data.

## Checks

The cleaned file was checked against the source for row counts, complaint IDs, product counts, and response counts. The saved file was also reloaded and checked.

The dataset still includes the partial January 2020 period. Each later analysis chooses its own date range.
