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


def validate_processed_data(df_clean: pd.DataFrame, df_raw: pd.DataFrame) -> dict[str, Any]:
    """Validate processed dataset against original raw source data."""
    if len(df_clean) != len(df_raw):
        raise ValueError(f"Row count mismatch: cleaned={len(df_clean)}, raw={len(df_raw)}.")

    if df_clean["complaint_id"].isna().any():
        raise ValueError("Found missing values in cleaned complaint_id.")
    if df_clean["complaint_id"].duplicated().any():
        raise ValueError("Found duplicate values in cleaned complaint_id.")
    if set(df_clean["complaint_id"]) != set(df_raw["complaint_id"]):
        raise ValueError("Cleaned complaint IDs do not match raw complaint IDs.")

    # Product and company response distributions must match raw source
    if df_clean["product"].value_counts().to_dict() != df_raw["product"].value_counts().to_dict():
        raise ValueError("Product category distribution changed during preparation.")
    if (
        df_clean["company_response_to_consumer"].value_counts().to_dict()
        != df_raw["company_response_to_consumer"].value_counts().to_dict()
    ):
        raise ValueError("Company response distribution changed during preparation.")

    # Derive expected outcome counts dynamically from raw source responses
    expected_ones = int(
        df_raw["company_response_to_consumer"].isin(
            ["Closed with monetary relief", "Closed with non-monetary relief"]
        ).sum()
    )
    expected_zeros = int(
        (df_raw["company_response_to_consumer"] == "Closed with explanation").sum()
    )
    expected_na = int((df_raw["company_response_to_consumer"] == "Untimely response").sum())

    actual_ones = int((df_clean["reported_relief"] == 1).sum())
    actual_zeros = int((df_clean["reported_relief"] == 0).sum())
    actual_na = int(df_clean["reported_relief"].isna().sum())

    if (actual_ones, actual_zeros, actual_na) != (expected_ones, expected_zeros, expected_na):
        raise ValueError(
            f"Relief mapping counts do not match raw source categories:\n"
            f"Expected: 1={expected_ones}, 0={expected_zeros}, NA={expected_na}\n"
            f"Actual:   1={actual_ones}, 0={actual_zeros}, NA={actual_na}"
        )

    # Narrative text and grouping validation
    if df_clean["consumer_complaint_narrative"].isna().sum() != df_raw["consumer_complaint_narrative"].isna().sum():
        raise ValueError("Missing narrative counts differ between raw and cleaned data.")

    # Expected columns: raw columns minus consumer_disputed plus reported_relief and narrative_group_id
    expected_cols = (set(df_raw.columns) - {"consumer_disputed"}) | {"reported_relief", "narrative_group_id"}
    if set(df_clean.columns) != expected_cols:
        missing_cols = expected_cols - set(df_clean.columns)
        extra_cols = set(df_clean.columns) - expected_cols
        raise ValueError(f"Schema mismatch: missing {missing_cols}, unexpected extra {extra_cols}.")

    distinct_groups = int(df_clean["narrative_group_id"].nunique(dropna=True))
    repeated_groups_count = int((df_clean["narrative_group_id"].value_counts() > 1).sum())
    repeated_rows_count = int(
        df_clean["narrative_group_id"].value_counts()[df_clean["narrative_group_id"].value_counts() > 1].sum()
    )

    return {
        "total_records": len(df_clean),
        "total_columns": len(df_clean.columns),
        "relief_ones": actual_ones,
        "relief_zeros": actual_zeros,
        "relief_na": actual_na,
        "distinct_narrative_groups": distinct_groups,
        "repeated_groups": repeated_groups_count,
        "repeated_rows": repeated_rows_count,
    }


def verify_saved_dataset(saved_path: str | Path, expected_df: pd.DataFrame) -> None:
    """Reload saved CSV and verify row count, IDs, outcome labels, group IDs, and text fields."""
    reloaded = pd.read_csv(saved_path, low_memory=False)
    if len(reloaded) != len(expected_df):
        raise ValueError(f"Reload verification failed: row count mismatch ({len(reloaded)} != {len(expected_df)}).")
    if not reloaded["complaint_id"].equals(expected_df["complaint_id"]):
        raise ValueError("Reload verification failed: complaint_id mismatch.")
    if int((reloaded["reported_relief"] == 1).sum()) != int((expected_df["reported_relief"] == 1).sum()):
        raise ValueError("Reload verification failed: relief outcome counts mismatch.")
    if int(reloaded["reported_relief"].isna().sum()) != int(expected_df["reported_relief"].isna().sum()):
        raise ValueError("Reload verification failed: relief missing counts mismatch.")
    if reloaded["narrative_group_id"].nunique() != expected_df["narrative_group_id"].nunique():
        raise ValueError("Reload verification failed: narrative group IDs mismatch.")

    # Verify ZIP codes remain string text
    sample_zips = expected_df["zip_code"].dropna().head(10).tolist()
    reloaded_zips = reloaded["zip_code"].dropna().head(10).tolist()
    if sample_zips != reloaded_zips:
        raise ValueError("Reload verification failed: zip code text representation mismatch.")


def prepare_dataset(
    config_path: str | Path = "config/settings.yaml",
) -> dict[str, Any]:
    """Execute end-to-end dataset preparation, validation, and export."""
    config = load_config(config_path)
    raw_file = config.get("data", {}).get("raw_file", "data/raw/complaints.csv.gz")
    clean_file = config.get("data", {}).get("clean_file", "data/processed/complaints_clean.csv.gz")
    expected_sha = config.get("source", {}).get("expected_sha256", "")

    verify_dataset_file(raw_file, expected_sha)

    raw_df = pd.read_csv(raw_file, low_memory=False)
    cleaned_df = prepare_complaints_data(raw_df)

    validation_summary = validate_processed_data(cleaned_df, raw_df)

    out_file_path = Path(clean_file)
    out_file_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(out_file_path, index=False, compression="gzip")

    verify_saved_dataset(out_file_path, cleaned_df)

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

