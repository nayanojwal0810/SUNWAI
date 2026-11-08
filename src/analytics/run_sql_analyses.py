"""Execute SQL analytical queries and generate findings report."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd

from src.data.profile_complaints import load_config

QUERY_SPECS: list[dict[str, Any]] = [
    {
        "filename": "01_monthly_complaints.sql",
        "output_csv": "monthly_complaints.csv",
        "expected_columns": ["month", "complaint_count", "prev_month_count", "mom_pct_change"],
    },
    {
        "filename": "02_product_distribution.sql",
        "output_csv": "product_distribution.csv",
        "expected_columns": ["product_name", "complaint_count", "percentage", "volume_rank"],
    },
    {
        "filename": "03_product_relief.sql",
        "output_csv": "product_relief.csv",
        "expected_columns": [
            "product_name",
            "total_complaints",
            "eligible_complaints",
            "relief_complaints",
            "explanation_complaints",
            "unlabeled_complaints",
            "relief_percentage",
        ],
    },
    {
        "filename": "04_company_volume.sql",
        "output_csv": "company_volume.csv",
        "expected_columns": [
            "company_name",
            "total_complaints",
            "percentage_of_all_complaints",
            "products_represented",
        ],
    },
    {
        "filename": "05_company_product_relief.sql",
        "output_csv": "company_product_relief.csv",
        "expected_columns": [
            "company_name",
            "product_name",
            "eligible_complaints",
            "relief_count",
            "relief_rate",
            "rank_in_product",
        ],
    },
    {
        "filename": "06_issues_by_product.sql",
        "output_csv": "issues_by_product.csv",
        "expected_columns": [
            "product_name",
            "issue",
            "complaint_count",
            "percentage_of_product_complaints",
            "issue_rank",
        ],
    },
    {
        "filename": "07_product_mix_benchmark.sql",
        "output_csv": "product_mix_benchmark.csv",
        "expected_columns": [
            "company_name",
            "eligible_complaints",
            "products_represented",
            "observed_relief_percentage",
            "expected_relief_percentage",
            "diff_percentage_points",
        ],
    },
    {
        "filename": "08_timely_responses.sql",
        "output_csv": "timely_responses.csv",
        "expected_columns": [
            "product_name",
            "total_complaints",
            "timely_count",
            "untimely_count",
            "unexpected_or_missing_count",
            "timely_percentage",
        ],
    },
]


def get_db_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open SQLite database in read-only mode."""
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database file not found: {path}")

    uri = f"file:///{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_query(conn: sqlite3.Connection, sql_path: str | Path) -> pd.DataFrame:
    """Read and execute a SQL file, returning results as a DataFrame."""
    path = Path(sql_path)
    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()

    return pd.read_sql_query(sql, conn)


def run_all_analyses(
    config_path: str | Path = "config/settings.yaml",
    sql_dir: str | Path = "sql/analysis",
    output_dir: str | Path = "outputs/sql",
) -> dict[str, Any]:
    """Run the SQL queries and save their result tables as CSV files."""
    config = load_config(config_path)
    db_file = config.get("data", {}).get("database_file", "data/processed/sunwai.sqlite3")

    conn = get_db_connection(db_file)
    sql_path = Path(sql_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        for spec in QUERY_SPECS:
            file_path = sql_path / spec["filename"]
            df = execute_query(conn, file_path)

            missing_cols = set(spec["expected_columns"]) - set(df.columns)
            if missing_cols:
                raise ValueError(
                    f"Query {spec['filename']} missing expected columns: {missing_cols}. Found: {df.columns.tolist()}"
                )

            csv_path = out_dir / spec["output_csv"]
            df.to_csv(csv_path, index=False)

    finally:
        conn.close()

    return {
        "queries_executed": len(QUERY_SPECS),
        "output_dir": str(out_dir).replace("\\", "/"),
    }


def main() -> None:
    """CLI entry point for running SQL business analyses."""
    results = run_all_analyses()
    print("SQL analysis completed.")
    print(f"Queries: {results['queries_executed']}")
    print(f"Output: {results['output_dir']}/")


if __name__ == "__main__":
    main()

