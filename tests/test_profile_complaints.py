"""Unit tests for dataset profiling metrics and verification functions."""

import gzip
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.data.profile_complaints import (
    calculate_sha256,
    compute_date_metrics,
    compute_narrative_metrics,
    compute_record_integrity_metrics,
    compute_structure_metrics,
    verify_dataset_file,
)


def test_compute_structure_metrics_counts_rows_and_missing() -> None:
    """Verify row counting, column counting, and missing value calculations."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "product": ["Mortgage", "Debt collection", None, "Credit card"],
            "score": [10.0, None, None, 40.0],
        }
    )

    metrics = compute_structure_metrics(df)
    assert metrics["total_rows"] == 4
    assert metrics["total_columns"] == 3

    cols = {c["column_name"]: c for c in metrics["columns"]}
    assert cols["id"]["missing_count"] == 0
    assert cols["id"]["missing_percentage"] == 0.0

    assert cols["product"]["missing_count"] == 1
    assert cols["product"]["missing_percentage"] == 25.0

    assert cols["score"]["missing_count"] == 2
    assert cols["score"]["missing_percentage"] == 50.0


def test_compute_record_integrity_duplicate_ids() -> None:
    """Verify unique identifier and duplicate counting on synthetic data."""
    df = pd.DataFrame(
        {
            "complaint_id": [101, 102, 102, 104, 105],
            "consumer_complaint_narrative": ["Text A", "Text B", "Text C", "Text D", "Text E"],
        }
    )

    integrity = compute_record_integrity_metrics(df)
    assert integrity["id_distinct_count"] == 4
    assert integrity["id_duplicate_count"] == 1
    assert integrity["id_missing_count"] == 0


def test_compute_record_integrity_repeated_narratives() -> None:
    """Verify detection of nonempty, blank, and repeated narratives."""
    df = pd.DataFrame(
        {
            "complaint_id": [1, 2, 3, 4, 5, 6],
            "consumer_complaint_narrative": [
                "Dispute regarding credit reporting.",
                "Dispute regarding credit reporting.",
                "Dispute regarding credit reporting.",
                "Different issue entirely.",
                "",
                None,
            ],
        }
    )

    integrity = compute_record_integrity_metrics(df)
    assert integrity["narrative_missing_count"] == 1
    assert integrity["narrative_blank_count"] == 2  # 1 None + 1 empty string
    assert integrity["narrative_nonempty_count"] == 4
    assert integrity["distinct_narratives"] == 2
    assert integrity["repeated_narrative_texts"] == 1  # 'Dispute regarding credit reporting.'
    assert integrity["repeated_narrative_rows"] == 3


def test_compute_narrative_metrics_lengths_and_redaction() -> None:
    """Verify narrative character length distributions and redaction detection."""
    df = pd.DataFrame(
        {
            "consumer_complaint_narrative": [
                "Short text",  # 10 chars
                "Account number XXXX is wrong",  # 28 chars, contains XXXX
                "A longer text for testing length distribution",  # 45 chars
            ]
        }
    )

    narr_metrics = compute_narrative_metrics(df)
    assert narr_metrics["nonempty_count"] == 3
    assert narr_metrics["min_length"] == 10
    assert narr_metrics["median_length"] == 28.0
    assert narr_metrics["max_length"] == 45
    assert narr_metrics["narratives_with_redaction"] == 1
    assert narr_metrics["redaction_percentage"] == round(1 / 3 * 100, 2)


def test_compute_date_metrics_valid_and_invalid() -> None:
    """Verify temporal parsing, date boundaries, and invalid value detection."""
    df = pd.DataFrame(
        {
            "date_received": ["2019-01-15", "2019-06-20", "invalid-date", None],
        }
    )

    date_metrics = compute_date_metrics(df, date_cols=["date_received"])
    stats = date_metrics["date_received"]
    assert stats["earliest_date"] == "2019-01-15"
    assert stats["latest_date"] == "2019-06-20"
    assert stats["missing_count"] == 1
    assert stats["invalid_count"] == 1


def test_verify_dataset_file_missing_file() -> None:
    """Verify that a missing dataset file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Dataset file not found"):
        verify_dataset_file("nonexistent/path/data.csv.gz", "dummyhash")


def test_verify_dataset_file_checksum_mismatch(tmp_path: Path) -> None:
    """Verify that an incorrect checksum raises ValueError with clear message."""
    gz_file = tmp_path / "test.csv.gz"
    with gzip.open(gz_file, "wb") as f:
        f.write(b"col1,col2\n1,2\n")

    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify_dataset_file(gz_file, "0000000000000000000000000000000000000000000000000000000000000000")


def test_verify_dataset_file_success(tmp_path: Path) -> None:
    """Verify that a valid gzip file with matching SHA-256 passes verification."""
    gz_file = tmp_path / "valid.csv.gz"
    with gzip.open(gz_file, "wb") as f:
        f.write(b"id,name\n1,Alice\n")

    expected_sha = calculate_sha256(gz_file)
    result = verify_dataset_file(gz_file, expected_sha)
    assert result["checksum_matched"] is True
    assert result["is_valid_gzip"] is True
    assert result["actual_sha256"] == expected_sha

