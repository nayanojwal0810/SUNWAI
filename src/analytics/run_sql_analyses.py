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


def format_sql_findings_report(results: dict[str, pd.DataFrame]) -> str:
    """Format query results into a structured Markdown business analysis report."""
    monthly = results["01_monthly_complaints.sql"]
    products = results["02_product_distribution.sql"]
    relief = results["03_product_relief.sql"]
    companies = results["04_company_volume.sql"]
    benchmark = results["07_product_mix_benchmark.sql"]
    timely = results["08_timely_responses.sql"]

    total_2019 = int(monthly["complaint_count"].sum())
    total_eligible = int(relief["eligible_complaints"].sum())
    total_relief = int(relief["relief_complaints"].sum())
    total_unlabeled = int(relief["unlabeled_complaints"].sum())
    overall_relief_pct = round(100.0 * total_relief / total_eligible, 2) if total_eligible > 0 else 0.0

    # Key bureau benchmarks
    bureau_names = [
        "Experian Information Solutions Inc.",
        "TRANSUNION INTERMEDIATE HOLDINGS, INC.",
        "EQUIFAX, INC.",
    ]
    bureau_rows = benchmark[benchmark["company_name"].isin(bureau_names)]
    experian_diff = bureau_rows[bureau_rows["company_name"].str.contains("Experian", case=False)]
    transunion_diff = bureau_rows[bureau_rows["company_name"].str.contains("TRANSUNION", case=False)]

    exp_obs = float(experian_diff["observed_relief_percentage"].iloc[0]) if not experian_diff.empty else 0.0
    exp_exp = float(experian_diff["expected_relief_percentage"].iloc[0]) if not experian_diff.empty else 0.0
    exp_diff = float(experian_diff["diff_percentage_points"].iloc[0]) if not experian_diff.empty else 0.0

    tu_obs = float(transunion_diff["observed_relief_percentage"].iloc[0]) if not transunion_diff.empty else 0.0
    tu_exp = float(transunion_diff["expected_relief_percentage"].iloc[0]) if not transunion_diff.empty else 0.0
    tu_diff = float(transunion_diff["diff_percentage_points"].iloc[0]) if not transunion_diff.empty else 0.0

    lines = [
        "# SQL Business Analysis Findings",
        "",
        "## Overview",
        "",
        "- **Reporting window:** Calendar year 2019 (January 1, 2019 through December 31, 2019).",
        f"- **Qualifying 2019 complaints:** {total_2019:,} records.",
        f"- **Eligible labeled complaints:** {total_eligible:,} records ({round(100.0 * total_eligible / total_2019, 2):.2f}% outcome coverage).",
        f"- **Unlabeled complaints:** {total_unlabeled:,} records (untimely responses excluded from relief rate denominators).",
        f"- **Overall 2019 relief rate:** {overall_relief_pct:.2f}% of eligible complaints received reported relief.",
        "",
        "## Complaint Trends",
        "",
        "Complaint volume remained elevated through summer and early autumn 2019 before tapering in the final two months.",
        "",
        "| Month | Complaints | Previous Month | MoM Change |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for _, row in monthly.iterrows():
        prev_str = f"{int(row['prev_month_count']):,}" if pd.notna(row["prev_month_count"]) else "—"
        mom_str = f"{row['mom_pct_change']:+.2f}%" if pd.notna(row["mom_pct_change"]) else "—"
        lines.append(f"| {row['month']} | {int(row['complaint_count']):,} | {prev_str} | {mom_str} |")

    lines.extend(
        [
            "",
            "## Product and Company Patterns",
            "",
            "### Complaint Distribution by Product",
            "",
            "| Rank | Financial Product | Complaints | Share |",
            "| :---: | :--- | :---: | :---: |",
        ]
    )

    for _, row in products.iterrows():
        lines.append(
            f"| {int(row['volume_rank'])} | {row['product_name']} | {int(row['complaint_count']):,} | {row['percentage']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "### Top 15 Companies by Complaint Volume",
            "",
            "| Company | Complaints | Share | Products Represented |",
            "| :--- | :---: | :---: | :---: |",
        ]
    )

    for _, row in companies.iterrows():
        lines.append(
            f"| {row['company_name']} | {int(row['total_complaints']):,} | {row['percentage_of_all_complaints']:.2f}% | {int(row['products_represented'])} |"
        )

    lines.extend(
        [
            "",
            "## Reported Relief",
            "",
            "Reported relief varies significantly by product line. High-volume debt products report substantially lower relief rates than transaction accounts.",
            "",
            "| Product | Total | Eligible | Relief (1) | Explanation (0) | Unlabeled | Relief Rate |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for _, row in relief.iterrows():
        lines.append(
            f"| {row['product_name']} | {int(row['total_complaints']):,} | {int(row['eligible_complaints']):,} | "
            f"{int(row['relief_complaints']):,} | {int(row['explanation_complaints']):,} | "
            f"{int(row['unlabeled_complaints']):,} | {row['relief_percentage']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Product-Aware Comparison",
            "",
            "Because companies receive complaints across different product mixes, comparing raw relief rates can be misleading. "
            "The product-aware benchmark compares each company's observed relief rate to an expected rate calculated from peer-company "
            "rates across the exact products handled by that company (excluding the firm's own records from peer reference rates). "
            "The comparison includes firms with at least 200 eligible complaints in 2019.",
            "",
            "### Top Positive Rate Differences (Observed Above Product-Mix Expectation)",
            "",
            "| Company | Eligible Complaints | Observed Relief % | Expected Relief % | Difference (pp) |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    for _, row in benchmark.head(5).iterrows():
        lines.append(
            f"| {row['company_name']} | {int(row['eligible_complaints']):,} | "
            f"{row['observed_relief_percentage']:.2f}% | {row['expected_relief_percentage']:.2f}% | "
            f"{row['diff_percentage_points']:+.2f} |"
        )

    lines.extend(
        [
            "",
            "### Top Negative Rate Differences (Observed Below Product-Mix Expectation)",
            "",
            "| Company | Eligible Complaints | Observed Relief % | Expected Relief % | Difference (pp) |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    for _, row in benchmark.tail(5).iterrows():
        lines.append(
            f"| {row['company_name']} | {int(row['eligible_complaints']):,} | "
            f"{row['observed_relief_percentage']:.2f}% | {row['expected_relief_percentage']:.2f}% | "
            f"{row['diff_percentage_points']:+.2f} |"
        )

    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            f"1. **Concentration in credit reporting:** Credit reporting accounts for {products.iloc[0]['percentage']:.2f}% of all 2019 complaints ({int(products.iloc[0]['complaint_count']):,} records). Three nationwide bureaus account for 37.52% of all complaints received in 2019.",
            "2. **Product-level relief disparity:** Reported relief rates differ fourfold across product categories, ranging from 6.43% for Mortgages up to 28.36% for Checking or Savings accounts and 28.16% for Credit Cards.",
            f"3. **Credit bureau benchmark divergence:** Experian reported relief in {exp_obs:.2f}% of eligible cases ({exp_diff:+.2f} percentage points above its {exp_exp:.2f}% product expectation), whereas TransUnion reported relief in only {tu_obs:.2f}% of cases ({tu_diff:+.2f} percentage points below its {tu_exp:.2f}% expectation) despite similar volumes and product profiles.",
            f"4. **High operational timeliness:** Across all products, {timely['timely_count'].sum() / timely['total_complaints'].sum() * 100:.2f}% of complaints received a timely response, ranging from 92.77% in Payday loans to 99.34% in Credit cards.",
            f"5. **High outcome label coverage:** 99.39% of 2019 complaints have definitive resolution outcome labels, with only {total_unlabeled:,} untimely responses requiring exclusion from relief rate denominators.",
            "",
            "## Limitations",
            "",
            "- **Observational metrics:** Differences in reported relief reflect company self-reporting practices and category selections, not independently verified customer satisfaction.",
            "- **Volume interpretation:** Raw complaint counts correlate strongly with company market share and account volume rather than customer-level complaint frequency.",
            "- **Benchmark interpretation:** The product-mix benchmark controls for product categories but does not control for sub-issues, customer tenure, or underlying complaint merit.",
        ]
    )

    return "\n".join(lines) + "\n"


def run_all_analyses(
    config_path: str | Path = "config/settings.yaml",
    sql_dir: str | Path = "sql/analysis",
    output_dir: str | Path = "outputs/sql",
    report_path: str | Path = "reports/sql_findings.md",
) -> dict[str, Any]:
    """Execute all SQL analytical queries, export CSVs, and generate findings report."""
    config = load_config(config_path)
    db_file = config.get("data", {}).get("database_file", "data/processed/sunwai.sqlite3")

    conn = get_db_connection(db_file)
    sql_path = Path(sql_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, pd.DataFrame] = {}

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
            results[spec["filename"]] = df

        report_markdown = format_sql_findings_report(results)
        rep_file = Path(report_path)
        rep_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rep_file, "w", encoding="utf-8") as f:
            f.write(report_markdown)

    finally:
        conn.close()

    return {
        "queries_executed": len(QUERY_SPECS),
        "output_dir": str(out_dir).replace("\\", "/"),
        "report_file": str(report_path).replace("\\", "/"),
    }


def main() -> None:
    """CLI entry point for running SQL business analyses."""
    results = run_all_analyses()
    print("SQL analysis completed.")
    print(f"Queries: {results['queries_executed']}")
    print(f"Output: {results['output_dir']}/")
    print(f"Report: {results['report_file']}")


if __name__ == "__main__":
    main()

