"""Business exploratory data analysis and statistical validation."""

from __future__ import annotations

import math
from pathlib import Path
import sqlite3
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from src.analytics.run_sql_analyses import get_db_connection
from src.data.profile_complaints import load_config

WILSON_Z: float = 1.959963984540054


def calculate_wilson_interval(
    n: int,
    x: int,
    z: float = WILSON_Z,
) -> tuple[float | None, float | None]:
    """Calculate 95% Wilson score confidence interval for a binomial proportion."""
    if n <= 0 or x < 0 or x > n:
        return None, None

    p = x / n
    z2 = z ** 2
    denominator = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denominator
    margin = (z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * (n ** 2)))) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return round(lower * 100.0, 2), round(upper * 100.0, 2)


def compute_product_relief_intervals(relief_df: pd.DataFrame) -> pd.DataFrame:
    """Add 95% Wilson confidence intervals to product-level reported-relief DataFrame."""
    expected_cols = {"product_name", "eligible_complaints", "relief_complaints", "relief_percentage"}
    missing = expected_cols - set(relief_df.columns)
    if missing:
        raise ValueError(f"Relief DataFrame missing columns: {missing}")

    records = []
    for _, row in relief_df.iterrows():
        n = int(row["eligible_complaints"])
        x = int(row["relief_complaints"])
        lower, upper = calculate_wilson_interval(n, x)
        records.append(
            {
                "product_name": str(row["product_name"]),
                "eligible_complaints": n,
                "relief_complaints": x,
                "relief_percentage": float(row["relief_percentage"]),
                "ci_lower": lower,
                "ci_upper": upper,
                "ci_width": round(upper - lower, 2) if lower is not None and upper is not None else None,
            }
        )

    return pd.DataFrame(records)


def perform_chi_square_test(relief_df: pd.DataFrame) -> dict[str, Any]:
    """Perform chi-square test of independence on product reported relief vs. explanation."""
    expected_cols = {"relief_complaints", "explanation_complaints"}
    missing = expected_cols - set(relief_df.columns)
    if missing:
        raise ValueError(f"Contingency DataFrame missing columns: {missing}")

    table = relief_df[["relief_complaints", "explanation_complaints"]].values
    if table.size == 0 or np.sum(table) == 0:
        raise ValueError("Cannot perform chi-square test on empty table.")

    chi2_stat, p_val, dof, _ = chi2_contingency(table)
    n = int(table.sum())
    r, c = table.shape
    min_dim = min(r - 1, c - 1)
    cramers_v = math.sqrt(chi2_stat / (n * min_dim)) if n > 0 and min_dim > 0 else 0.0

    return {
        "chi2_stat": round(float(chi2_stat), 4),
        "p_value": float(p_val),
        "p_value_formatted": "< 0.0001" if p_val < 0.0001 else f"{p_val:.4f}",
        "dof": int(dof),
        "total_observations": n,
        "cramers_v": round(float(cramers_v), 4),
    }


def compute_product_period_sensitivity(
    conn: sqlite3.Connection,
    fy_relief_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare product-level reported-relief rates between full-year 2019 and Jan-Oct 2019."""
    query = """
    SELECT
        p.product_name,
        SUM(CASE WHEN f.reported_relief IN (0, 1) THEN 1 ELSE 0 END) AS eligible_complaints,
        ROUND(100.0 * SUM(CASE WHEN f.reported_relief = 1 THEN 1 ELSE 0 END) /
              NULLIF(SUM(CASE WHEN f.reported_relief IN (0, 1) THEN 1 ELSE 0 END), 0), 2) AS relief_percentage
    FROM fact_complaints f
    JOIN dim_products p ON f.product_id = p.product_id
    WHERE f.date_received >= '2019-01-01'
      AND f.date_received < '2019-11-01'
    GROUP BY p.product_id, p.product_name
    """
    jo_df = pd.read_sql_query(query, conn)

    merged = fy_relief_df[["product_name", "eligible_complaints", "relief_percentage"]].merge(
        jo_df,
        on="product_name",
        suffixes=("_full_year", "_jan_oct"),
    )

    merged["diff_percentage_points"] = (
        merged["relief_percentage_full_year"] - merged["relief_percentage_jan_oct"]
    ).round(2)
    merged["abs_diff_pp"] = merged["diff_percentage_points"].abs()

    return merged.sort_values(by="abs_diff_pp", ascending=False).reset_index(drop=True)


def compute_company_benchmark(
    conn: sqlite3.Connection,
    start_date: str = "2019-01-01",
    end_date: str = "2020-01-01",
    min_company_complaints: int = 200,
    min_peer_eligible: int = 1,
) -> pd.DataFrame:
    """Calculate product-aware company expected relief benchmark independently in Python."""
    query = f"""
    SELECT
        f.company_id,
        c.company_name,
        f.product_id,
        COUNT(*) AS cp_eligible,
        SUM(f.reported_relief) AS cp_relief
    FROM fact_complaints f
    JOIN dim_companies c ON f.company_id = c.company_id
    WHERE f.date_received >= '{start_date}'
      AND f.date_received < '{end_date}'
      AND f.reported_relief IN (0, 1)
    GROUP BY f.company_id, c.company_name, f.product_id
    """
    df = pd.read_sql_query(query, conn)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "company_name",
                "products_represented",
                "eligible_complaints",
                "observed_relief_percentage",
                "expected_relief_percentage",
                "diff_percentage_points",
            ]
        )

    prod_totals = (
        df.groupby("product_id")
        .agg(total_prod_eligible=("cp_eligible", "sum"), total_prod_relief=("cp_relief", "sum"))
        .reset_index()
    )

    merged = df.merge(prod_totals, on="product_id")
    merged["peer_eligible"] = merged["total_prod_eligible"] - merged["cp_eligible"]
    merged["peer_relief"] = merged["total_prod_relief"] - merged["cp_relief"]

    merged["valid_peer"] = merged["peer_eligible"] >= min_peer_eligible
    merged["peer_rate"] = np.where(
        merged["valid_peer"],
        merged["peer_relief"] / merged["peer_eligible"],
        np.nan,
    )
    merged["expected_relief_count"] = merged["cp_eligible"] * merged["peer_rate"]

    company_groups = (
        merged.groupby(["company_id", "company_name"])
        .agg(
            products_represented=("product_id", "nunique"),
            eligible_complaints=("cp_eligible", "sum"),
            observed_relief_count=("cp_relief", "sum"),
            expected_relief_count=("expected_relief_count", "sum"),
            missing_peers=("valid_peer", lambda x: int((~x).sum())),
        )
        .reset_index()
    )

    qualified = company_groups[
        (company_groups["eligible_complaints"] >= min_company_complaints)
        & (company_groups["missing_peers"] == 0)
    ].copy()

    if qualified.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "company_name",
                "products_represented",
                "eligible_complaints",
                "observed_relief_percentage",
                "expected_relief_percentage",
                "diff_percentage_points",
            ]
        )

    qualified["observed_relief_percentage"] = (
        100.0 * qualified["observed_relief_count"] / qualified["eligible_complaints"]
    ).round(2)
    qualified["expected_relief_percentage"] = (
        100.0 * qualified["expected_relief_count"] / qualified["eligible_complaints"]
    ).round(2)
    qualified["diff_percentage_points"] = (
        100.0
        * (qualified["observed_relief_count"] - qualified["expected_relief_count"])
        / qualified["eligible_complaints"]
    ).round(2)

    return qualified.sort_values(by="diff_percentage_points", ascending=False).reset_index(drop=True)


def audit_company_benchmark(
    conn: sqlite3.Connection,
    sql_benchmark_df: pd.DataFrame,
) -> dict[str, Any]:
    """Audit SQL benchmark against Python implementation, check peer support and period sensitivity."""
    py_baseline = compute_company_benchmark(conn, "2019-01-01", "2020-01-01", 200, 1)

    py_companies = set(py_baseline["company_name"])
    sql_companies = set(sql_benchmark_df["company_name"])
    if py_companies != sql_companies:
        missing_in_py = sql_companies - py_companies
        missing_in_sql = py_companies - sql_companies
        raise ValueError(
            f"Company set mismatch between Python and SQL benchmark. "
            f"In SQL but not Python: {missing_in_py}. In Python but not SQL: {missing_in_sql}."
        )

    comp_merged = py_baseline.merge(sql_benchmark_df, on="company_name", suffixes=("_py", "_sql"))

    eligible_mismatches = comp_merged[
        comp_merged["eligible_complaints_py"] != comp_merged["eligible_complaints_sql"]
    ]
    if not eligible_mismatches.empty:
        sample = eligible_mismatches.iloc[0]
        raise ValueError(
            f"Eligible complaint count mismatch for '{sample['company_name']}': "
            f"Python={sample['eligible_complaints_py']}, SQL={sample['eligible_complaints_sql']}."
        )

    obs_diff = (comp_merged["observed_relief_percentage_py"] - comp_merged["observed_relief_percentage_sql"]).abs()
    exp_diff = (comp_merged["expected_relief_percentage_py"] - comp_merged["expected_relief_percentage_sql"]).abs()
    gap_diff = (comp_merged["diff_percentage_points_py"] - comp_merged["diff_percentage_points_sql"]).abs()

    max_obs_diff = float(obs_diff.max()) if not obs_diff.empty else 0.0
    max_exp_diff = float(exp_diff.max()) if not exp_diff.empty else 0.0
    max_gap_diff = float(gap_diff.max()) if not gap_diff.empty else 0.0

    if max_obs_diff > 0.02:
        worst = comp_merged.loc[obs_diff.idxmax()]
        raise ValueError(
            f"Observed relief percentage discrepancy ({max_obs_diff:.4f} pp) exceeds 0.02 pp threshold "
            f"for '{worst['company_name']}' (Python={worst['observed_relief_percentage_py']}, SQL={worst['observed_relief_percentage_sql']})."
        )
    if max_exp_diff > 0.02:
        worst = comp_merged.loc[exp_diff.idxmax()]
        raise ValueError(
            f"Expected relief percentage discrepancy ({max_exp_diff:.4f} pp) exceeds 0.02 pp threshold "
            f"for '{worst['company_name']}' (Python={worst['expected_relief_percentage_py']}, SQL={worst['expected_relief_percentage_sql']})."
        )
    if max_gap_diff > 0.02:
        worst = comp_merged.loc[gap_diff.idxmax()]
        raise ValueError(
            f"Adjusted difference discrepancy ({max_gap_diff:.4f} pp) exceeds 0.02 pp threshold "
            f"for '{worst['company_name']}' (Python={worst['diff_percentage_points_py']}, SQL={worst['diff_percentage_points_sql']})."
        )

    max_rate_discrepancy = max(max_obs_diff, max_exp_diff, max_gap_diff)

    py_strict = compute_company_benchmark(conn, "2019-01-01", "2020-01-01", 200, 20)
    py_janoct_strict = compute_company_benchmark(conn, "2019-01-01", "2019-11-01", 200, 20)

    top3_companies = sql_benchmark_df.sort_values(by="eligible_complaints", ascending=False).head(3)
    top3_comparison: list[dict[str, Any]] = []

    for _, row in top3_companies.iterrows():
        cname = str(row["company_name"])
        fy_row = py_strict[py_strict["company_name"] == cname]
        jo_row = py_janoct_strict[py_janoct_strict["company_name"] == cname]

        fy_diff = float(fy_row["diff_percentage_points"].iloc[0]) if not fy_row.empty else None
        jo_diff = float(jo_row["diff_percentage_points"].iloc[0]) if not jo_row.empty else None
        shift = round(jo_diff - fy_diff, 2) if fy_diff is not None and jo_diff is not None else None

        top3_comparison.append(
            {
                "company_name": cname,
                "eligible_complaints_fy": int(row["eligible_complaints"]),
                "full_year_diff_pp": fy_diff,
                "jan_oct_diff_pp": jo_diff,
                "shift_pp": shift,
                "qualifies_both": (not fy_row.empty) and (not jo_row.empty),
            }
        )

    return {
        "sql_count": len(sql_benchmark_df),
        "py_baseline_count": len(py_baseline),
        "py_strict_count": len(py_strict),
        "py_janoct_strict_count": len(py_janoct_strict),
        "max_diff_py_vs_sql": max_rate_discrepancy,
        "max_rate_discrepancy": max_rate_discrepancy,
        "max_obs_diff": max_obs_diff,
        "max_exp_diff": max_exp_diff,
        "max_gap_diff": max_gap_diff,
        "top3_comparison": top3_comparison,
    }


def generate_figures(
    products_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    relief_ci_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    output_dir: str | Path = "outputs/figures/business",
) -> list[str]:
    """Generate and save four focused analytical visualizations."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    saved_files: list[str] = []

    # Chart 1: Product Complaints
    fig, ax = plt.subplots(figsize=(10, 6))
    sorted_prods = products_df.sort_values(by="complaint_count", ascending=True)
    bars = ax.barh(sorted_prods["product_name"], sorted_prods["complaint_count"], color="#2b5c8f")
    ax.set_xlabel("Number of Complaints (2019)", fontsize=11)
    ax.set_title("CFPB Complaint Volume by Financial Product (2019)", fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    max_val = sorted_prods["complaint_count"].max()
    for bar in bars:
        w = bar.get_width()
        ax.text(
            w + max_val * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{int(w):,}",
            va="center",
            ha="left",
            fontsize=9,
            color="#222222",
        )
    ax.set_xlim(0, max_val * 1.15)
    plt.tight_layout()
    p1 = out_path / "product_complaints.png"
    fig.savefig(p1, dpi=300)
    plt.close(fig)
    saved_files.append(str(p1).replace("\\", "/"))

    # Chart 2: Monthly Complaints
    fig, ax = plt.subplots(figsize=(10, 5.2))
    colors = ["#2b5c8f"] * 10 + ["#d97736", "#d97736"]
    bars = ax.bar(monthly_df["month"], monthly_df["complaint_count"], color=colors, width=0.65)
    ax.set_ylabel("Complaints Received", fontsize=11)
    ax.set_xlabel("Month (2019)", fontsize=11)
    ax.set_title("2019 Monthly Complaint Volume", fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.xticks(rotation=45, ha="right")

    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 150,
            f"{int(h):,}",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    ax.set_ylim(0, monthly_df["complaint_count"].max() * 1.20)
    ax.text(
        0.98,
        0.90,
        "Orange bars: Reporting & snapshot lag\nmay contribute to lower late-2019 counts",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff2e6", edgecolor="#d97736", alpha=0.9),
    )
    plt.tight_layout()
    p2 = out_path / "monthly_complaints.png"
    fig.savefig(p2, dpi=300)
    plt.close(fig)
    saved_files.append(str(p2).replace("\\", "/"))

    # Chart 3: Product Relief Intervals
    sorted_relief = relief_ci_df.sort_values(by="relief_percentage", ascending=True)
    err_low = sorted_relief["relief_percentage"] - sorted_relief["ci_lower"]
    err_high = sorted_relief["ci_upper"] - sorted_relief["relief_percentage"]

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = range(len(sorted_relief))
    ax.errorbar(
        sorted_relief["relief_percentage"],
        y_pos,
        xerr=[err_low, err_high],
        fmt="o",
        color="#1f77b4",
        ecolor="#333333",
        elinewidth=1.5,
        capsize=4,
        markersize=6,
    )
    labels = [
        f"{row['product_name']}\n(n={int(row['eligible_complaints']):,})"
        for _, row in sorted_relief.iterrows()
    ]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("Reported Relief Rate (%) with 95% Wilson CI", fontsize=11)
    ax.set_title(
        "Product Reported-Relief Rates and 95% Wilson Confidence Intervals (2019)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    for y, (_, row) in enumerate(sorted_relief.iterrows()):
        pct = row["relief_percentage"]
        ax.text(
            pct + 0.6,
            y,
            f"{pct:.2f}% [{row['ci_lower']:.2f}%, {row['ci_upper']:.2f}%]",
            va="center",
            ha="left",
            fontsize=8,
            color="#333333",
        )
    ax.set_xlim(0, 36)
    plt.tight_layout()
    p3 = out_path / "product_relief_intervals.png"
    fig.savefig(p3, dpi=300)
    plt.close(fig)
    saved_files.append(str(p3).replace("\\", "/"))

    # Chart 4: Company Adjusted Gaps (Top 12 by sample size)
    top12 = (
        benchmark_df.sort_values(by="eligible_complaints", ascending=False)
        .head(12)
        .sort_values(by="diff_percentage_points", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6.8))
    bar_colors = ["#2b5c8f" if d >= 0 else "#c0392b" for d in top12["diff_percentage_points"]]
    y_pos = range(len(top12))
    bars = ax.barh(y_pos, top12["diff_percentage_points"], color=bar_colors, height=0.65)
    ax.axvline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)

    labels = [
        f"{row['company_name']}\n(n={int(row['eligible_complaints']):,})"
        for _, row in top12.iterrows()
    ]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("Product-Mix Adjusted Rate Difference (percentage points)", fontsize=11)
    ax.set_title(
        "Product-Mix Adjusted Relief Differences for 12 Largest Qualifying Companies",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    for bar, d in zip(bars, top12["diff_percentage_points"]):
        if d >= 0:
            ax.text(
                d + 0.6,
                bar.get_y() + bar.get_height() / 2,
                f"{d:+.2f} pp",
                va="center",
                ha="left",
                fontsize=8.5,
                fontweight="bold",
                color="#1c3d5a",
            )
        else:
            ax.text(
                d - 0.6,
                bar.get_y() + bar.get_height() / 2,
                f"{d:+.2f} pp",
                va="center",
                ha="right",
                fontsize=8.5,
                fontweight="bold",
                color="#7b1f15",
            )

    min_x = min(top12["diff_percentage_points"].min() - 5, -28)
    max_x = max(top12["diff_percentage_points"].max() + 5, 35)
    ax.set_xlim(min_x, max_x)

    fig.text(
        0.5,
        0.01,
        "Note: Descriptive comparison against product peers (excluding firm's own complaints). Not a measure of overall customer service quality.",
        ha="center",
        fontsize=8,
        style="italic",
        color="#555555",
    )
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    p4 = out_path / "company_adjusted_gaps.png"
    fig.savefig(p4, dpi=300)
    plt.close(fig)
    saved_files.append(str(p4).replace("\\", "/"))

    return saved_files


def run_business_analysis(
    config_path: str | Path = "config/settings.yaml",
    sql_output_dir: str | Path = "outputs/sql",
    figures_dir: str | Path = "outputs/figures/business",
) -> dict[str, Any]:
    """Run business statistics, benchmark checks, and chart exports."""
    config = load_config(config_path)
    db_file = config.get("data", {}).get("database_file", "data/processed/sunwai.sqlite3")

    sql_dir = Path(sql_output_dir)
    relief_csv = sql_dir / "product_relief.csv"
    products_csv = sql_dir / "product_distribution.csv"
    monthly_csv = sql_dir / "monthly_complaints.csv"
    benchmark_csv = sql_dir / "product_mix_benchmark.csv"

    for path in (relief_csv, products_csv, monthly_csv, benchmark_csv):
        if not path.is_file():
            raise FileNotFoundError(f"Required SQL output not found: {path}. Run SQL analyses first.")

    relief_df = pd.read_csv(relief_csv)
    products_df = pd.read_csv(products_csv)
    monthly_df = pd.read_csv(monthly_csv)
    benchmark_df = pd.read_csv(benchmark_csv)

    conn = get_db_connection(db_file)
    try:
        relief_ci_df = compute_product_relief_intervals(relief_df)
        chi2_results = perform_chi_square_test(relief_df)
        period_sens_df = compute_product_period_sensitivity(conn, relief_df)
        audit_results = audit_company_benchmark(conn, benchmark_df)

        results: dict[str, Any] = {
            "product_relief_ci": relief_ci_df,
            "chi_square": chi2_results,
            "product_period_sensitivity": period_sens_df,
            "benchmark_audit": audit_results,
        }

        created_figures = generate_figures(
            products_df=products_df,
            monthly_df=monthly_df,
            relief_ci_df=relief_ci_df,
            benchmark_df=benchmark_df,
            output_dir=figures_dir,
        )
        results["created_figures"] = created_figures

    finally:
        conn.close()

    return results


def main() -> None:
    """CLI entry point for business EDA and statistical analysis."""
    results = run_business_analysis()
    chi2 = results["chi_square"]
    audit = results["benchmark_audit"]
    figures = results["created_figures"]

    print("Business analysis completed successfully.")
    print(f"Eligible complaints analyzed: {chi2['total_observations']:,}")
    print(f"Chi-square: {chi2['chi2_stat']} (p {chi2['p_value_formatted']}, Cramér's V = {chi2['cramers_v']})")
    print(f"Benchmark companies checked: {audit['sql_count']}")
    print(f"Figures generated: {len(figures)} files")


if __name__ == "__main__":
    main()

