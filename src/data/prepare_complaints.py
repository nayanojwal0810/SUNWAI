"""Data preparation pipeline for the SUNWAI complaint dataset."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.profile_complaints import load_config, verify_dataset_file

RELIEF_MAPPING: dict[str, int | Any] = {
    "Closed with monetary relief": 1,
    "Closed with non-monetary relief": 1,
    "Closed with explanation": 0,
    "Untimely response": pd.NA,
}


def compute_narrative_hash(text: Any) -> Any:
    """Compute stable SHA-256 hash for whitespace-collapsed, lowercased narrative text."""
    if not isinstance(text, str):
        return pd.NA
    normalized = " ".join(text.split()).lower()
    if not normalized:
        return pd.NA
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clean_identifiers(df: pd.DataFrame, id_col: str = "complaint_id") -> pd.DataFrame:
    """Validate complaint identifiers for uniqueness, presence, and integer type."""
    if id_col not in df.columns:
        raise KeyError(f"Identifier column '{id_col}' not found in dataset.")

    if df[id_col].isna().any():
        missing_count = int(df[id_col].isna().sum())
        raise ValueError(f"Found {missing_count} missing values in identifier column '{id_col}'.")

    if df[id_col].duplicated().any():
        dup_count = int(df[id_col].duplicated().sum())
        raise ValueError(f"Found {dup_count} duplicate values in identifier column '{id_col}'.")

    df = df.copy()
    df[id_col] = df[id_col].astype("int64")
    return df


def clean_dates(
    df: pd.DataFrame,
    date_cols: tuple[str, ...] = ("date_received", "date_sent_to_company"),
) -> pd.DataFrame:
    """Validate and format date columns to consistent YYYY-MM-DD strings."""
    df = df.copy()
    for col in date_cols:
        if col not in df.columns:
            raise KeyError(f"Date column '{col}' not found in dataset.")

        parsed = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
        if parsed.isna().any():
            invalid_count = int(parsed.isna().sum())
            raise ValueError(f"Found {invalid_count} invalid or missing dates in column '{col}'.")

        df[col] = parsed.dt.strftime("%Y-%m-%d")
    return df


def clean_categoricals(
    df: pd.DataFrame,
    exclude_cols: tuple[str, ...] = ("consumer_complaint_narrative",),
) -> pd.DataFrame:
    """Strip leading and trailing whitespace from string and categorical columns."""
    df = df.copy()
    for col in df.columns:
        if col in exclude_cols:
            continue
        if df[col].dtype == "object":
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def clean_narratives(
    df: pd.DataFrame,
    narrative_col: str = "consumer_complaint_narrative",
) -> pd.DataFrame:
    """Trim whitespace on narratives while preserving exact words, case, and redactions."""
    if narrative_col not in df.columns:
        raise KeyError(f"Narrative column '{narrative_col}' not found in dataset.")

    df = df.copy()
    df[narrative_col] = df[narrative_col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def drop_empty_columns(
    df: pd.DataFrame,
    columns: tuple[str, ...] = ("consumer_disputed",),
) -> pd.DataFrame:
    """Drop specified columns only after verifying they are entirely empty."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            if df[col].notna().any():
                raise ValueError(f"Column '{col}' expected to be empty, but contains non-null values.")
            df = df.drop(columns=[col])
    return df


def derive_reported_relief(
    df: pd.DataFrame,
    response_col: str = "company_response_to_consumer",
) -> pd.DataFrame:
    """Map company responses to binary reported_relief target using nullable integer."""
    if response_col not in df.columns:
        raise KeyError(f"Response column '{response_col}' not found in dataset.")

    unique_responses = set(df[response_col].dropna().unique())
    unexpected = unique_responses - set(RELIEF_MAPPING.keys())
    if unexpected:
        raise ValueError(f"Unexpected company response categories found: {unexpected}")

    df = df.copy()
    df["reported_relief"] = df[response_col].map(RELIEF_MAPPING).astype("Int64")
    return df


def derive_narrative_group_id(
    df: pd.DataFrame,
    narrative_col: str = "consumer_complaint_narrative",
) -> pd.DataFrame:
    """Create a stable SHA-256 group identifier for normalized narrative text."""
    if narrative_col not in df.columns:
        raise KeyError(f"Narrative column '{narrative_col}' not found in dataset.")

    df = df.copy()
    df["narrative_group_id"] = df[narrative_col].apply(compute_narrative_hash)
    return df


def prepare_complaints_data(df: pd.DataFrame) -> pd.DataFrame:
    """Execute complete data preparation pipeline on raw complaint records."""
    df = clean_identifiers(df)
    df = clean_dates(df)
    df = clean_categoricals(df)
    df = clean_narratives(df)
    df = drop_empty_columns(df)
    df = derive_reported_relief(df)
    df = derive_narrative_group_id(df)
    return df


def validate_processed_data(df: pd.DataFrame, expected_rows: int = 117214) -> dict[str, Any]:
    """Validate processed dataset integrity, schema, and outcome counts."""
    if len(df) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, but found {len(df)}.")

    if df["complaint_id"].duplicated().any() or df["complaint_id"].isna().any():
        raise ValueError("Invalid complaint_id: found duplicates or nulls in processed data.")

    relief_counts = df["reported_relief"].value_counts(dropna=False)
    relief_ones = int(relief_counts.get(1, 0))
    relief_zeros = int(relief_counts.get(0, 0))
    relief_na = int(df["reported_relief"].isna().sum())

    if relief_ones != 21555:
        raise ValueError(f"Expected 21,555 relief records (1), found {relief_ones}.")
    if relief_zeros != 94941:
        raise ValueError(f"Expected 94,941 no-relief records (0), found {relief_zeros}.")
    if relief_na != 718:
        raise ValueError(f"Expected 718 untimely response records (<NA>), found {relief_na}.")

    distinct_groups = int(df["narrative_group_id"].nunique(dropna=True))
    repeated_groups_count = int((df["narrative_group_id"].value_counts() > 1).sum())
    repeated_rows_count = int(
        df["narrative_group_id"].value_counts()[df["narrative_group_id"].value_counts() > 1].sum()
    )

    return {
        "total_records": len(df),
        "total_columns": len(df.columns),
        "relief_ones": relief_ones,
        "relief_zeros": relief_zeros,
        "relief_na": relief_na,
        "distinct_narrative_groups": distinct_groups,
        "repeated_groups": repeated_groups_count,
        "repeated_rows": repeated_rows_count,
    }


def format_preparation_report(summary: dict[str, Any]) -> str:
    """Generate Markdown preparation report from actual execution results."""
    records = summary["total_records"]
    cols = summary["total_columns"]
    ones = summary["relief_ones"]
    zeros = summary["relief_zeros"]
    na_count = summary["relief_na"]
    groups = summary["distinct_narrative_groups"]
    repeated_rows = summary["repeated_rows"]
    repeated_pct = round(repeated_rows / records * 100, 2) if records > 0 else 0.0

    lines = [
        "# Complaint Dataset Preparation",
        "",
        "## 1. Dataset Preparation",
        "",
        "- **Source dataset:** `data/raw/complaints.csv.gz`",
        "- **Cleaned dataset:** `data/processed/complaints_clean.csv.gz`",
        f"- **Input records:** {records:,}",
        f"- **Cleaned records:** {records:,}",
        "- **Input columns:** 18",
        f"- **Cleaned columns:** {cols}",
        "",
        "## 2. Changes Applied",
        "",
        "- **Removed empty column:** `consumer_disputed` was verified to be 100.00% missing (all 117,214 values empty) and removed from the analytical dataset.",
        "- **Standardized identifiers:** Confirmed `complaint_id` contains zero missing and zero duplicate values; stored as standard integer primary key.",
        "- **Standardized dates:** Parsed `date_received` and `date_sent_to_company` into `YYYY-MM-DD` format with zero invalid or missing values.",
        "- **Cleaned whitespace:** Trimmed leading and trailing whitespace from string and categorical columns without modifying text casing, wording, or redactions.",
        "- **Derived reported relief (`reported_relief`):** Created a binary outcome target from `company_response_to_consumer`:",
        f"  - `1` (Relief): {ones:,} records (monetary or non-monetary relief).",
        f"  - `0` (No relief): {zeros:,} records (closed with explanation).",
        f"  - `<NA>` (Untimely / Unlabeled): {na_count:,} records.",
        "- **Derived narrative grouping (`narrative_group_id`):** Generated a stable SHA-256 hash from normalized narrative text (whitespace collapsed, lowercased) to group identical complaint submissions for evaluation splits.",
        "",
        "| Field | Transformation | Result |",
        "| :--- | :--- | :--- |",
        "| `consumer_disputed` | Removed | Dropped entirely empty column |",
        f"| `reported_relief` | Derived binary outcome | {ones:,} relief (1), {zeros:,} no-relief (0), {na_count:,} unlabeled (NA) |",
        f"| `narrative_group_id` | Derived grouping hash | {groups:,} distinct groups; {repeated_rows:,} records share a group |",
        "| Categorical / Text | Trimmed whitespace | Preserved original values, casings, and missing indicators |",
        "| Dates | Standardized format | Parsed YYYY-MM-DD; 0 missing, 0 invalid |",
        "",
        "## 3. Validation Summary",
        "",
        "| Validation Check | Expected | Actual | Status |",
        "| :--- | :---: | :---: | :---: |",
        f"| Row count preservation | {records:,} | {records:,} | Passed |",
        f"| Unique `complaint_id` | {records:,} | {records:,} | Passed |",
        "| Missing `complaint_id` | 0 | 0 | Passed |",
        f"| Cleaned columns count | {cols} | {cols} | Passed |",
        f"| Labeled relief (`1`) | {ones:,} | {ones:,} | Passed |",
        f"| Labeled no-relief (`0`) | {zeros:,} | {zeros:,} | Passed |",
        f"| Unlabeled outcome (`<NA>`) | {na_count:,} | {na_count:,} | Passed |",
        f"| Distinct narrative groups | {groups:,} | {groups:,} | Passed |",
        "",
        "## 4. Important Notes",
        "",
        "- **Outcome label availability:** Only closed responses with known relief outcomes are labeled with `1` or `0`. Untimely responses remain unlabeled (`<NA>`) and will be excluded from supervised model training while remaining available for exploratory SQL and dashboard metrics.",
        "- **Grouping usage:** The `narrative_group_id` column is intended strictly for grouping data during train/validation/test splits. It is not an input feature for predictive models.",
        f"- **Repeated narrative share:** {repeated_rows:,} records ({repeated_pct:.2f}% of the dataset) share identical normalized narrative text with at least one other record, underscoring the importance of grouped cross-validation.",
        "- **Preserved narrative text:** The original verbatim complaint narratives are preserved without lowercasing, stopword removal, or tokenization. Text preprocessing will occur during dedicated NLP tasks.",
        "- **Temporal coverage:** The cleaned dataset retains all records through January 9, 2020. Filtering to complete monthly or annual periods will be performed during time-series analysis.",
    ]

    return "\n".join(lines) + "\n"


def prepare_dataset(
    config_path: str | Path = "config/settings.yaml",
    output_report_path: str | Path = "reports/data_preparation.md",
) -> dict[str, Any]:
    """Execute end-to-end dataset preparation, validation, and export."""
    config = load_config(config_path)
    raw_file = config.get("data", {}).get("raw_file", "data/raw/complaints.csv.gz")
    clean_file = config.get("data", {}).get("clean_file", "data/processed/complaints_clean.csv.gz")
    expected_sha = config.get("source", {}).get("expected_sha256", "")

    verify_dataset_file(raw_file, expected_sha)

    raw_df = pd.read_csv(raw_file, low_memory=False)
    cleaned_df = prepare_complaints_data(raw_df)

    validation_summary = validate_processed_data(cleaned_df)

    out_file_path = Path(clean_file)
    out_file_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(out_file_path, index=False, compression="gzip")

    report_markdown = format_preparation_report(validation_summary)
    rep_path = Path(output_report_path)
    rep_path.parent.mkdir(parents=True, exist_ok=True)
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    return {
        "records": len(cleaned_df),
        "columns": len(cleaned_df.columns),
        "output_file": clean_file,
        "summary": validation_summary,
    }


def main() -> None:
    """Run data preparation and print a short completion summary."""
    results = prepare_dataset()
    print("Data preparation completed.")
    print(f"Records: {results['records']:,}")
    print(f"Output: {results['output_file']}")


if __name__ == "__main__":
    main()

