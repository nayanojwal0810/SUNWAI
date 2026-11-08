"""Dataset profiling script for SUNWAI complaint data."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_config(config_path: str | Path = "config/settings.yaml") -> dict[str, Any]:
    """Load the project YAML configuration file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration format in {path}")
    return config


def calculate_sha256(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of a file."""
    path = Path(file_path)
    sha256 = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_dataset_file(file_path: str | Path, expected_sha256: str) -> dict[str, Any]:
    """Verify that the raw dataset exists, is valid gzip, and matches the checksum."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise ValueError(f"Dataset file is empty: {path}")

    try:
        with gzip.open(path, "rb") as gz:
            if not gz.read(64):
                raise ValueError(f"Failed to read gzip header from {path}")
    except Exception as exc:
        raise ValueError(f"Invalid gzip format in {path}: {exc}") from exc

    actual_sha256 = calculate_sha256(path)
    if actual_sha256.lower() != expected_sha256.lower():
        raise ValueError(f"Checksum mismatch for {path}")

    return {
        "file_path": path.as_posix(),
        "file_size_bytes": file_size,
        "actual_sha256": actual_sha256,
        "checksum_matched": True,
    }


def compute_structure_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Calculate basic row, column, and missing-value counts."""
    total_rows = len(df)
    columns_info = []

    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_pct = (missing_count / total_rows * 100) if total_rows > 0 else 0.0
        columns_info.append(
            {
                "column_name": col,
                "data_type": str(df[col].dtype),
                "missing_count": missing_count,
                "missing_percentage": round(missing_pct, 2),
            }
        )

    return {
        "total_rows": total_rows,
        "total_columns": len(df.columns),
        "columns": columns_info,
    }


def compute_record_integrity_metrics(
    df: pd.DataFrame,
    id_col: str = "complaint_id",
    narrative_col: str = "consumer_complaint_narrative",
) -> dict[str, Any]:
    """Calculate identifier uniqueness, missing IDs, and narrative counts."""
    total_rows = len(df)
    results: dict[str, Any] = {
        "id_column": id_col,
        "id_missing_count": 0,
        "id_distinct_count": 0,
        "id_duplicate_count": 0,
        "narrative_missing_count": 0,
        "narrative_blank_count": 0,
        "narrative_nonempty_count": 0,
        "narrative_coverage_pct": 0.0,
        "distinct_narratives": 0,
        "repeated_narrative_texts": 0,
        "repeated_narrative_rows": 0,
    }

    if id_col in df.columns:
        id_series = df[id_col]
        missing_ids = int(id_series.isna().sum())
        valid_ids = id_series.dropna()
        distinct_ids = int(valid_ids.nunique())
        duplicate_ids = int(len(valid_ids) - distinct_ids)

        results["id_missing_count"] = missing_ids
        results["id_distinct_count"] = distinct_ids
        results["id_duplicate_count"] = duplicate_ids

    if narrative_col in df.columns:
        narr_series = df[narrative_col]
        missing_narr = int(narr_series.isna().sum())
        clean_text = narr_series.dropna().astype(str).str.strip()
        nonempty_text = clean_text[clean_text != ""]
        blank_count = missing_narr + int((clean_text == "").sum())

        counts = nonempty_text.value_counts()
        repeated_texts = int((counts > 1).sum())
        repeated_rows = int(counts[counts > 1].sum())

        results["narrative_missing_count"] = missing_narr
        results["narrative_blank_count"] = blank_count
        results["narrative_nonempty_count"] = len(nonempty_text)
        results["narrative_coverage_pct"] = (
            round(len(nonempty_text) / total_rows * 100, 2) if total_rows > 0 else 0.0
        )
        results["distinct_narratives"] = int(nonempty_text.nunique())
        results["repeated_narrative_texts"] = repeated_texts
        results["repeated_narrative_rows"] = repeated_rows

    return results


def compute_narrative_metrics(
    df: pd.DataFrame,
    narrative_col: str = "consumer_complaint_narrative",
) -> dict[str, Any]:
    """Calculate character lengths and redaction presence for non-empty narratives."""
    if narrative_col not in df.columns:
        return {}

    clean_text = df[narrative_col].dropna().astype(str).str.strip()
    valid_text = clean_text[clean_text != ""]
    if len(valid_text) == 0:
        return {
            "nonempty_count": 0,
            "min_length": 0,
            "median_length": 0.0,
            "max_length": 0,
            "narratives_with_redaction": 0,
            "redaction_percentage": 0.0,
        }

    lengths = valid_text.str.len()
    has_redaction = int(valid_text.str.contains("XXXX", regex=False).sum())

    return {
        "nonempty_count": len(valid_text),
        "min_length": int(lengths.min()),
        "median_length": round(float(lengths.median()), 2),
        "max_length": int(lengths.max()),
        "narratives_with_redaction": has_redaction,
        "redaction_percentage": round(has_redaction / len(valid_text) * 100, 2),
    }


def compute_date_metrics(
    df: pd.DataFrame,
    date_cols: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate date ranges and check for missing or invalid dates."""
    if date_cols is None:
        date_cols = ["date_received", "date_sent_to_company"]

    results: dict[str, Any] = {}
    for col in date_cols:
        if col not in df.columns:
            continue
        missing_count = int(df[col].isna().sum())
        parsed = pd.to_datetime(df[col], errors="coerce")
        invalid_count = int(parsed.isna().sum()) - missing_count

        earliest = str(parsed.min().strftime("%Y-%m-%d")) if parsed.notna().any() else "N/A"
        latest = str(parsed.max().strftime("%Y-%m-%d")) if parsed.notna().any() else "N/A"

        results[col] = {
            "earliest_date": earliest,
            "latest_date": latest,
            "missing_count": missing_count,
            "invalid_count": invalid_count,
        }
    return results


def compute_categorical_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Extract category distributions for core business fields."""
    total_rows = len(df)
    results: dict[str, Any] = {}

    def get_counts(col_name: str, top_n: int | None = None) -> list[dict[str, Any]]:
        if col_name not in df.columns:
            return []
        series = df[col_name].fillna("[Missing]")
        vc = series.value_counts()
        if top_n is not None:
            vc = vc.head(top_n)
        return [
            {
                "category": str(cat),
                "count": int(count),
                "percentage": round(count / total_rows * 100, 2) if total_rows > 0 else 0.0,
            }
            for cat, count in vc.items()
        ]

    results["products"] = get_counts("product")
    results["company_responses"] = get_counts("company_response_to_consumer")
    results["top_companies"] = get_counts("company", top_n=10)
    results["distinct_companies"] = int(df["company"].nunique()) if "company" in df.columns else 0
    results["distinct_states"] = int(df["state"].nunique()) if "state" in df.columns else 0

    if "date_received" in df.columns:
        parsed_dates = pd.to_datetime(df["date_received"], errors="coerce")
        jan_2020 = int((parsed_dates >= "2020-01-01").sum())
        results["jan_2020_count"] = jan_2020

    return results


def profile_dataset(
    config_path: str | Path = "config/settings.yaml",
) -> dict[str, Any]:
    """Calculate the dataset profile and return its measurements."""
    config = load_config(config_path)
    raw_file = config.get("data", {}).get("raw_file", "data/raw/complaints.csv.gz")
    expected_sha = config.get("source", {}).get("expected_sha256", "")

    verification = verify_dataset_file(raw_file, expected_sha)
    df = pd.read_csv(raw_file, low_memory=False)

    structure_metrics = compute_structure_metrics(df)
    integrity_metrics = compute_record_integrity_metrics(df)
    narrative_metrics = compute_narrative_metrics(df)
    date_metrics = compute_date_metrics(df)
    categorical_metrics = compute_categorical_metrics(df)

    profile_results = {
        "verification": verification,
        "structure": structure_metrics,
        "integrity": integrity_metrics,
        "narrative": narrative_metrics,
        "dates": date_metrics,
        "categories": categorical_metrics,
    }

    return profile_results


def main() -> None:
    """Run dataset profiling and print a simple summary."""
    results = profile_dataset()
    rows = results["structure"]["total_rows"]
    cols = results["structure"]["total_columns"]
    print("Dataset profiling completed.")
    print(f"Records: {rows:,} | Columns: {cols}")


if __name__ == "__main__":
    main()
