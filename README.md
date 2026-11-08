# SUNWAI — Financial Consumer Complaint Intelligence

## Project Overview

SUNWAI analyzes historical US Consumer Financial Protection Bureau (CFPB) complaints to understand recurring customer issues and evaluate company responses. By combining structured complaint fields with written customer narratives, the project explores patterns in complaints and examines whether narrative text provides useful insights beyond standard category codes.

The project has completed initial dataset profiling, data preparation, relational database creation, SQL business analysis, and business exploratory data analysis (EDA). Using an indexed SQLite database (`data/processed/sunwai.sqlite3`), the project analyzes full-calendar-year 2019 complaint volumes, product distributions, reported relief rates, and product-aware peer company benchmarks. Statistical and robustness checks evaluate sampling uncertainty with Wilson confidence intervals, assess product outcome disparities using chi-square analysis, and audit company benchmarks across observation windows. NLP models, machine-learning classifiers, and dashboards have not yet been built.

## Dataset

The project uses a historical extract from the CFPB Consumer Complaint Database covering January 2019 through early January 2020. Every record in this extract contains a customer-written complaint narrative submitted online with publication consent.

- **Source agency:** [Consumer Financial Protection Bureau (CFPB)](https://www.consumerfinance.gov/data-research/consumer-complaints/)
- **Historical distribution:** Distributed by Emil Hvitfeldt and Julia Silge for [*Supervised Machine Learning for Text Analysis in R*](https://github.com/EmilHvitfeldt/smltar).
- **Direct download:** [complaints.csv.gz](https://raw.githubusercontent.com/EmilHvitfeldt/smltar/3ae4ab3e7ce53e3d74dded5f17e7cf8dbe164caa/data/complaints.csv.gz)

## Tools and Technologies

- **Python 3.11:** Core programming language.
- **pandas:** Data manipulation and summary calculations.
- **SciPy:** Statistical tests of independence and contingency analysis.
- **Matplotlib:** Business charts and visualization.
- **SQLite:** Relational database storage for structured complaints and dimension tables.
- **PyYAML:** Configuration file loading.
- **pytest:** Unit testing framework.

Later stages will add tools for text processing, classical machine learning, and an interactive dashboard (Streamlit).

## Project Workflow

The planned project workflow includes:

1. **Dataset profiling:** Inspecting schema, missing values, record integrity, and category distributions.
2. **Data preparation:** Cleaning fields, standardizing categories, and resolving duplicate text.
3. **Relational storage:** Organizing structured complaint records in SQLite for SQL analysis.
4. **Natural language processing:** Extracting key themes and terms from customer complaint narratives.
5. **Outcome analysis and modeling:** Evaluating factors associated with company relief responses using classical machine learning.
6. **Interactive dashboard:** Presenting findings through an exploratory Streamlit application.

## Getting Started

### Prerequisites

- Python 3.11
- Git

### Installation

1. Clone the repository and move into the project directory:

   ```bash
   git clone https://github.com/nayanojwal0810/SUNWAI.git
   cd SUNWAI
   ```

2. Create and activate a virtual environment:

   ```powershell
   # Windows PowerShell:
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   ```bash
   # macOS / Linux:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install project dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Place the raw dataset in `data/raw/`:

   ```powershell
   # Windows PowerShell:
   New-Item -ItemType Directory -Force -Path data/raw
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/EmilHvitfeldt/smltar/3ae4ab3e7ce53e3d74dded5f17e7cf8dbe164caa/data/complaints.csv.gz" -OutFile "data/raw/complaints.csv.gz"
   ```

5. Run dataset profiling, data preparation, database creation, SQL analysis, business EDA, and tests:

   ```bash
   python src/data/profile_complaints.py
   python -m src.data.prepare_complaints
   python -m src.data.build_database
   python -m src.analytics.run_sql_analyses
   python -m src.analytics.analyze_business
   python -m pytest -q
   ```

## Project Files

- `sql/schema.sql`: Relational database schema and index definitions for SQLite.
- `sql/analysis/`: Analytical SQL queries examining monthly volume, product relief, company volume, issues, product-mix benchmarks, and timeliness.
- `src/data/profile_complaints.py`: Script that inspects the raw dataset and calculates summary statistics.
- `src/data/prepare_complaints.py`: Script that cleans data fields, maps reported relief outcomes, groups narratives, and exports the processed dataset.
- `src/data/build_database.py`: Script that initializes the SQLite database, populates dimension and fact tables, and validates data integrity.
- `src/analytics/run_sql_analyses.py`: Script that executes the SQL analytical queries, exports CSV summaries to `outputs/sql/`, and generates the findings report.
- `src/analytics/analyze_business.py`: Script that performs business exploratory data analysis, computes Wilson confidence intervals, conducts chi-square tests, audits company benchmarks, and creates visual charts.
- `docs/data_dictionary.md`: [Data Dictionary](docs/data_dictionary.md) explaining all original and prepared dataset columns.
- `docs/database_schema.md`: [Database Schema](docs/database_schema.md) describing table structures, relationships, and constraints.
- `reports/data_profile.md`: [Data Profile Report](reports/data_profile.md) detailing dataset quality and distributions.
- `reports/data_preparation.md`: [Data Preparation Report](reports/data_preparation.md) detailing data cleaning changes, relief label distributions, and validation checks.
- `reports/sql_findings.md`: [SQL Business Analysis Findings](reports/sql_findings.md) detailing monthly trends, product-level relief rates, and product-mix-adjusted company comparisons.
- `reports/business_findings.md`: [Business Analysis Findings](reports/business_findings.md) detailing statistical uncertainty, product-level relief confidence intervals, and benchmark robustness across observation windows.
- `tests/test_profile_complaints.py`: Unit tests for profiling and verification functions.
- `tests/test_prepare_complaints.py`: Unit tests for data cleaning, relief mapping, and narrative grouping.
- `tests/test_build_database.py`: Unit tests for database table creation, foreign key checks, and rebuilding mechanics.
- `tests/test_sql_analyses.py`: Unit tests for SQL analytical queries, MoM calculations, and product-mix benchmarks.
- `tests/test_business_analysis.py`: Unit tests for Wilson score intervals, chi-square contingency tests, period sensitivity, and independent benchmark calculations.
- `config/settings.yaml`: Project paths and configuration settings.
- `requirements.txt`: Initial Python dependencies.

## Data Limitations

- **Selection bias:** The dataset contains only complaints where consumers chose to submit a written narrative online and consented to publish it.
- **Missing dispute information:** The `consumer_disputed` field is completely empty because the CFPB stopped collecting this information in early 2017.
- **Duplicate narratives:** Several thousand records share identical complaint text, likely from form letters or batch submissions.
- **Reporting window:** The data ends on January 9, 2020. January 2020 contains only a partial month of data.
- **Self-reported outcomes:** Company responses reflect what companies reported to the CFPB, not verified consumer satisfaction.
