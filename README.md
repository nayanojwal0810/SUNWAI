# SUNWAI

SUNWAI examines written consumer complaints about financial services. The project uses Python and SQL to find common problems, compare reported company responses, and study the complaint text.

The data comes from a historical sample of US consumer complaints published by the Consumer Financial Protection Bureau (CFPB). It is not a study of Indian financial complaints.

## What the project looks at

- Which financial products receive the most complaints?
- How often do companies report monetary or non-monetary relief?
- How do company results compare after accounting for their different product mixes?
- What can we learn from the written complaints beyond the selected issue categories?

## Data

The dataset contains 117,214 complaints received between January 1, 2019 and January 9, 2020. Every record has a published complaint narrative. Most business comparisons use only complaints received in 2019 (116,679 records).

Download the historical dataset: [complaints.csv.gz](https://raw.githubusercontent.com/EmilHvitfeldt/smltar/3ae4ab3e7ce53e3d74dded5f17e7cf8dbe164caa/data/complaints.csv.gz).

This is a selected historical sample, not every CFPB complaint. A company reporting relief does not necessarily mean the consumer was satisfied.

## Findings so far

- Credit reporting accounts for 47.29% of complaints in the 2019 sample.
- Reported relief ranges from 6.43% for mortgage complaints to 28.36% for checking or savings account complaints.
- Comparing companies by product mix reveals differences that raw complaint counts cannot explain.
- Some written complaints repeat: 16.27% of records share normalized narrative text with at least one other complaint.

These are observations about this dataset. They do not establish which company gives better service.

## Run the project

Use Python 3.11. Clone the repository and install the requirements:

    git clone https://github.com/nayanojwal0810/SUNWAI.git
    cd SUNWAI
    pip install -r requirements.txt

Download the file linked above and save it as data/raw/complaints.csv.gz. Then run these commands from the repository root, in order:

    python src/data/profile_complaints.py
    python -m src.data.prepare_complaints
    python -m src.data.build_database
    python -m src.analytics.run_sql_analyses
    python -m src.analytics.analyze_business
    python -m src.nlp.prepare_text
    python -m pytest -q

The scripts create local data files, SQL result tables, and charts. These files are not included in GitHub.

## Read the results

- [Data overview](reports/data_profile.md)
- [Data cleaning](reports/data_preparation.md)
- [SQL findings](reports/sql_findings.md)
- [Business and statistical findings](reports/business_findings.md)
- [Complaint text findings](reports/text_profile.md)

For field definitions and database tables, see [data dictionary](docs/data_dictionary.md) and [database guide](docs/database_schema.md).

Reports are written summaries of the current dataset. Running the Python scripts does not rewrite them.

## Current work

Data preparation, SQL analysis, statistics, and text profiling are in place. Complaint themes, predictive models, and an interactive dashboard are planned but not yet completed.
