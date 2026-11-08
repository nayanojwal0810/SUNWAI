# SUNWAI - Financial Consumer Complaint Intelligence & Decision-Support Analytics

## Business Problem

Financial institutions process thousands of customer disputes and service complaints across diverse products such as credit cards, mortgages, and student loans. Unresolved consumer friction increases customer churn, regulatory scrutiny, and operational overhead. Identifying recurring issues early and understanding why customers submit formal complaints is essential for effective risk mitigation and consumer protection.

## Purpose of Analyzing Historical Complaints

Analyzing historical complaints helps organizations uncover patterns in customer dissatisfaction, understand drivers behind disputes, and evaluate company responses. By systematically examining complaints, risk managers and operations teams can prioritize recurring pain points, measure resolution effectiveness, and make informed, data-driven decisions to improve customer trust.

## Dataset and Sources

This project uses a historical extract from the Consumer Financial Protection Bureau (CFPB) Consumer Complaint Database.

- Original agency source: [Consumer Financial Protection Bureau (CFPB)](https://www.consumerfinance.gov/data-research/consumer-complaints/)
- Pinned historical distribution: Distributed by Emil Hvitfeldt and Julia Silge for [*Supervised Machine Learning for Text Analysis in R* (SMLTAR)](https://github.com/EmilHvitfeldt/smltar).
- Download URL: [complaints.csv.gz](https://raw.githubusercontent.com/EmilHvitfeldt/smltar/3ae4ab3e7ce53e3d74dded5f17e7cf8dbe164caa/data/complaints.csv.gz)
- Expected SHA-256: `f4a5e174d364f1e1a25fac324e1a8224ff4e9454326e6e58abaa194bca93097b`

The dataset contains structured complaint records, company responses, consumer disputed flags, and narrative descriptions submitted by consumers.

## Planned Analytical Workflow

The planned end-to-end analytics workflow will encompass:

1. **Data Ingestion and Integrity:** Verifying raw file integrity and loading structured data into clean tabular formats.
2. **Relational Modeling (SQL):** Storing and querying structured complaint records using SQLite for repeatable aggregation and reporting.
3. **Exploratory Data Analysis:** Evaluating complaint distributions across financial products, submission channels, and companies.
4. **Natural Language Processing (NLP):** Processing free-form complaint narratives through tokenization, n-gram analysis, and keyword extraction.
5. **Machine Learning:** Training and evaluating classical machine-learning models to explore complaint outcomes and classification patterns.
6. **Decision-Support Dashboard:** Presenting summary metrics and exploratory findings in an interactive Streamlit interface.

## Current Project Status

The initial project foundation and raw dataset profiling have been completed. The raw dataset integrity has been verified, all 18 fields are documented in the data dictionary, and an initial dataset profile report has been generated. No data cleaning pipelines, feature engineering, database tables, analytical models, or dashboards have been built yet.

## Data Profiling

To verify the raw dataset integrity and generate the technical profiling report, run:

```bash
python src/data/profile_complaints.py
```

Detailed documentation and generated profiling outputs:
- [Data Dictionary](docs/data_dictionary.md): Field definitions, data types, missing rates, and planned project roles.
- [Data Profiling Report](reports/data_profile.md): Detailed structural metrics, narrative coverage, category distributions, and data-quality findings.

## Data Limitations

When working with historical CFPB complaint data, several limitations apply:

- **Self-Selection Bias:** Complaints reflect consumers who encountered friction severe enough to file a federal complaint, not the entire customer population.
- **Narrative Availability:** Consumer narrative opt-ins were not present across all reporting periods, so text narratives represent a subset of overall records.
- **Company Context:** Complaint volume is strongly correlated with company size and customer base volume rather than complaint rate per transaction.
- **Historical Snapshot:** Pinned historical extracts reflect a specific capture window and do not represent live operational records.

## Environment Setup and Installation

### Prerequisites

- Python 3.11
- Git

### Setup Steps

1. Clone the repository and navigate into the project directory:

   ```bash
   git clone https://github.com/nayanojwal0810/SUNWAI.git
   cd SUNWAI
   ```

2. Create and activate a Python 3.11 virtual environment:

   ```bash
   python -m venv .venv
   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install the initial project dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Place the raw dataset at `data/raw/complaints.csv.gz`:

   ```bash
   mkdir -p data/raw
   # Download the pinned historical dataset file:
   curl -Lo data/raw/complaints.csv.gz https://raw.githubusercontent.com/EmilHvitfeldt/smltar/3ae4ab3e7ce53e3d74dded5f17e7cf8dbe164caa/data/complaints.csv.gz
   ```

5. Confirm the SHA-256 checksum matches `f4a5e174d364f1e1a25fac324e1a8224ff4e9454326e6e58abaa194bca93097b`.

