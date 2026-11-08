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
    label_coverage_pct = round(100.0 * total_eligible / total_2019, 2) if total_2019 > 0 else 0.0

    lines = [
        "# SQL Business Analysis Findings",
        "",
        "## Overview",
        "",
        "- **Reporting window:** Calendar year 2019 (January 1, 2019 through December 31, 2019).",
        f"- **Qualifying 2019 complaints:** {total_2019:,} records.",
        f"- **Eligible labeled complaints:** {total_eligible:,} records ({label_coverage_pct:.2f}% outcome coverage).",
        f"- **Unlabeled complaints:** {total_unlabeled:,} records (untimely responses excluded from relief rate denominators).",
        f"- **Overall 2019 relief rate:** {overall_relief_pct:.2f}% of eligible complaints received reported relief.",
        "",
        "## Complaint Trends",
        "",
        "In this historical extract, recorded complaints remained elevated from spring through October 2019 before declining in November and December. Reporting lags and snapshot coverage may contribute to the observed decline, so the extract alone cannot establish a market-wide reduction in consumer complaints.",
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
            "The product-aware benchmark calculates an expected relief rate for each company based on peer-company rates within the "
            "specific products handled by that firm. For each company-product pair, peer reference rates exclude that company's own "
            "records so that individual firms do not influence their own benchmark. Because companies operate across distinct sets "
            "of products, different companies may have different reference groups.",
            "",
            "The comparison includes firms with at least 200 eligible complaints in 2019 where peer references are available across "
            "all products handled by the company. Observed differences highlight variations warranting further investigation rather "
            "than conclusive proof of service quality, and they should not be interpreted as causal outcomes.",
            "",
            "### Top Positive Rate Differences (Observed Above Product-Mix Expectation)",
            "",
            "| Company | Eligible Complaints | Observed Relief % | Expected Relief % | Difference (pp) |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    if benchmark.empty:
        lines.append("| — | — | — | — | — |")
    else:
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

    if benchmark.empty:
        lines.append("| — | — | — | — | — |")
    else:
        for _, row in benchmark.tail(5).iterrows():
            lines.append(
                f"| {row['company_name']} | {int(row['eligible_complaints']):,} | "
                f"{row['observed_relief_percentage']:.2f}% | {row['expected_relief_percentage']:.2f}% | "
                f"{row['diff_percentage_points']:+.2f} |"
            )

    # Dynamic calculation of key findings
    if not products.empty:
        top_prod = products.iloc[0]
        top_prod_name = top_prod["product_name"]
        top_prod_share = float(top_prod["percentage"])
        top_prod_count = int(top_prod["complaint_count"])
    else:
        top_prod_name = "N/A"
        top_prod_share = 0.0
        top_prod_count = 0

    if not companies.empty:
        top_n = min(3, len(companies))
        top_share = float(companies.head(top_n)["percentage_of_all_complaints"].sum())
        num_words = {1: "single", 2: "top two", 3: "top three"}
        prefix = num_words.get(top_n, f"top {top_n}")
        top_companies_text = f"The {prefix} companies by volume account for {top_share:.2f}% of all complaints received in 2019."
    else:
        top_companies_text = "Company concentration data is unavailable."

    finding_1 = (
        f"1. **Concentration in top product category:** {top_prod_name} accounts for {top_prod_share:.2f}% "
        f"of all 2019 complaints ({top_prod_count:,} records). {top_companies_text}"
    )

    valid_relief = relief[relief["eligible_complaints"] > 0]
    if not valid_relief.empty:
        max_relief_row = valid_relief.loc[valid_relief["relief_percentage"].idxmax()]
        min_relief_row = valid_relief.loc[valid_relief["relief_percentage"].idxmin()]
        max_relief_prod = max_relief_row["product_name"]
        max_relief_pct = float(max_relief_row["relief_percentage"])
        min_relief_prod = min_relief_row["product_name"]
        min_relief_pct = float(min_relief_row["relief_percentage"])
        finding_2 = (
            f"2. **Product-level relief disparity:** Reported relief rates differ across product categories, "
            f"ranging from {min_relief_pct:.2f}% for {min_relief_prod} up to {max_relief_pct:.2f}% for {max_relief_prod}."
        )
    else:
        finding_2 = "2. **Product-level relief disparity:** Product-level relief data is unavailable."

    if len(benchmark) >= 2:
        top_pos = benchmark.iloc[0]
        top_neg = benchmark.iloc[-1]
        finding_3 = (
            f"3. **Product-mix benchmark differences:** Among qualifying companies (at least 200 eligible complaints), "
            f"product-adjusted rate differences ranged from {float(top_neg['diff_percentage_points']):+.2f} percentage points "
            f"({top_neg['company_name']}: {float(top_neg['observed_relief_percentage']):.2f}% observed vs. "
            f"{float(top_neg['expected_relief_percentage']):.2f}% expected) to "
            f"{float(top_pos['diff_percentage_points']):+.2f} percentage points "
            f"({top_pos['company_name']}: {float(top_pos['observed_relief_percentage']):.2f}% observed vs. "
            f"{float(top_pos['expected_relief_percentage']):.2f}% expected). "
            f"These differences reflect comparisons against product peers rather than uniform institutional service quality."
        )
    elif len(benchmark) == 1:
        single = benchmark.iloc[0]
        finding_3 = (
            f"3. **Product-mix benchmark differences:** Only one company met the qualification threshold "
            f"({single['company_name']}: {float(single['observed_relief_percentage']):.2f}% observed vs. "
            f"{float(single['expected_relief_percentage']):.2f}% expected, difference of "
            f"{float(single['diff_percentage_points']):+.2f} percentage points)."
        )
    else:
        finding_3 = (
            "3. **Product-mix benchmark differences:** Benchmark comparison is unavailable because no companies "
            "met the qualification threshold of 200 eligible complaints with complete peer references."
        )

    total_timely_complaints = int(timely["total_complaints"].sum())
    overall_timely_pct = (
        round(100.0 * timely["timely_count"].sum() / total_timely_complaints, 2)
        if total_timely_complaints > 0
        else 0.0
    )
    valid_timely = timely[timely["total_complaints"] > 0]
    if not valid_timely.empty:
        max_timely_row = valid_timely.loc[valid_timely["timely_percentage"].idxmax()]
        min_timely_row = valid_timely.loc[valid_timely["timely_percentage"].idxmin()]
        max_timely_prod = max_timely_row["product_name"]
        max_timely_pct = float(max_timely_row["timely_percentage"])
        min_timely_prod = min_timely_row["product_name"]
        min_timely_pct = float(min_timely_row["timely_percentage"])
        finding_4 = (
            f"4. **High operational timeliness:** Across all products, {overall_timely_pct:.2f}% of complaints "
            f"received a timely response, ranging from {min_timely_pct:.2f}% in {min_timely_prod} "
            f"to {max_timely_pct:.2f}% in {max_timely_prod}."
        )
    else:
        finding_4 = f"4. **High operational timeliness:** Across all products, {overall_timely_pct:.2f}% of complaints received a timely response."

    finding_5 = (
        f"5. **High outcome label coverage:** {label_coverage_pct:.2f}% of 2019 complaints have definitive "
        f"resolution outcome labels, with only {total_unlabeled:,} untimely responses requiring exclusion "
        f"from relief rate denominators."
    )

    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            finding_1,
            finding_2,
            finding_3,
            finding_4,
            finding_5,
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

