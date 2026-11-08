"""Unit tests for SQL business analysis queries using synthetic in-memory SQLite data."""

from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from src.analytics.run_sql_analyses import execute_query, format_sql_findings_report


@pytest.fixture
def memory_db() -> sqlite3.Connection:
    """Create an in-memory SQLite database initialized with project schema."""
    conn = sqlite3.connect(":memory:")
    with open("sql/schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dim_products (product_id, product_name)
        VALUES (1, 'Credit card'), (2, 'Mortgage'), (3, 'Specialty');
    """)
    cursor.execute("""
        INSERT INTO dim_companies (company_id, company_name)
        VALUES (1, 'Company Alpha'), (2, 'Company Beta'), (3, 'Company Solo');
    """)
    cursor.execute("""
        INSERT INTO dim_states (state_id, state_code)
        VALUES (1, 'CA'), (2, 'NY');
    """)
    conn.commit()
    yield conn
    conn.close()


def test_monthly_complaints_mom_and_2020_exclusion(memory_db: sqlite3.Connection) -> None:
    records = [
        # Jan 2019: 100 complaints
        *[(i, "2019-01-15", "2019-01-15", 1, 1, "Narrative", "Closed with explanation", 0, "h") for i in range(1, 101)],
        # Feb 2019: 150 complaints (+50.0%)
        *[(i, "2019-02-15", "2019-02-15", 1, 1, "Narrative", "Closed with explanation", 0, "h") for i in range(101, 251)],
        # Jan 2020: 50 complaints (Must be excluded from 2019 analysis)
        *[(i, "2020-01-05", "2020-01-05", 1, 1, "Narrative", "Closed with explanation", 0, "h") for i in range(251, 301)],
    ]
    memory_db.executemany(
        """
        INSERT INTO fact_complaints (
            complaint_id, date_received, date_sent_to_company, product_id, company_id,
            consumer_complaint_narrative, company_response_to_consumer, reported_relief, narrative_group_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        records,
    )
    memory_db.commit()

    df = execute_query(memory_db, "sql/analysis/01_monthly_complaints.sql")
    assert len(df) == 2
    assert df["month"].tolist() == ["2019-01", "2019-02"]
    assert df["complaint_count"].tolist() == [100, 150]
    assert pd.isna(df["prev_month_count"].iloc[0])
    assert pd.isna(df["mom_pct_change"].iloc[0])
    assert df["prev_month_count"].iloc[1] == 100
    assert df["mom_pct_change"].iloc[1] == 50.0


def test_product_relief_denominator_excludes_null(memory_db: sqlite3.Connection) -> None:
    records = [
        # Product 1 (Credit card): 10 relief=1, 30 relief=0, 10 relief=NULL (unlabeled)
        *[(i, "2019-05-01", "2019-05-01", 1, 1, "Narrative", "Closed with monetary relief", 1, "h") for i in range(1, 11)],
        *[(i, "2019-05-01", "2019-05-01", 1, 1, "Narrative", "Closed with explanation", 0, "h") for i in range(11, 41)],
        *[(i, "2019-05-01", "2019-05-01", 1, 1, "Narrative", "Untimely response", None, "h") for i in range(41, 51)],
        # 2020 record (excluded)
        (51, "2020-01-02", "2020-01-02", 1, 1, "Narrative", "Closed with monetary relief", 1, "h"),
    ]
    memory_db.executemany(
        """
        INSERT INTO fact_complaints (
            complaint_id, date_received, date_sent_to_company, product_id, company_id,
            consumer_complaint_narrative, company_response_to_consumer, reported_relief, narrative_group_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        records,
    )
    memory_db.commit()

    df = execute_query(memory_db, "sql/analysis/03_product_relief.sql")
    p1 = df[df["product_name"] == "Credit card"].iloc[0]
    assert p1["total_complaints"] == 50
    assert p1["eligible_complaints"] == 40  # 10 + 30
    assert p1["relief_complaints"] == 10
    assert p1["explanation_complaints"] == 30
    assert p1["unlabeled_complaints"] == 10
    assert p1["relief_percentage"] == 25.0  # 10 / 40 * 100


def test_product_mix_benchmark_calculation(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Alpha (Company 1) in Product 1: 100 relief=1, 100 relief=0 (200 total)
    for _ in range(100):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(100):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "text", "Closed with explanation", 0, "h"))
        cid += 1

    # Alpha in Product 2: 20 relief=1, 80 relief=0 (100 total)
    for _ in range(20):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(80):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "text", "Closed with explanation", 0, "h"))
        cid += 1

    # Beta (Company 2) in Product 1: 50 relief=1, 150 relief=0 (200 total)
    for _ in range(50):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(150):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "text", "Closed with explanation", 0, "h"))
        cid += 1

    # Beta in Product 2: 30 relief=1, 270 relief=0 (300 total)
    for _ in range(30):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 2, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(270):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 2, "text", "Closed with explanation", 0, "h"))
        cid += 1

    # Solo (Company 3) in Product 3: 250 relief=1 (No peers in Product 3; must be excluded from benchmark)
    for _ in range(250):
        records.append((cid, "2019-05-01", "2019-05-01", 3, 3, "text", "Closed with monetary relief", 1, "h"))
        cid += 1

    memory_db.executemany(
        """
        INSERT INTO fact_complaints (
            complaint_id, date_received, date_sent_to_company, product_id, company_id,
            consumer_complaint_narrative, company_response_to_consumer, reported_relief, narrative_group_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        records,
    )
    memory_db.commit()

    df = execute_query(memory_db, "sql/analysis/07_product_mix_benchmark.sql")

    # Only Alpha (300 complaints) and Beta (500 complaints) should qualify
    assert len(df) == 2
    assert "Company Solo" not in df["company_name"].values

    alpha = df[df["company_name"] == "Company Alpha"].iloc[0]
    assert alpha["eligible_complaints"] == 300
    assert alpha["observed_relief_percentage"] == 40.0
    assert alpha["expected_relief_percentage"] == 20.0
    assert alpha["diff_percentage_points"] == 20.0

    beta = df[df["company_name"] == "Company Beta"].iloc[0]
    assert beta["eligible_complaints"] == 500
    assert beta["observed_relief_percentage"] == 16.0
    assert beta["expected_relief_percentage"] == 32.0
    assert beta["diff_percentage_points"] == -16.0


def test_timely_responses_calculation(memory_db: sqlite3.Connection) -> None:
    records = [
        (1, "2019-02-01", "2019-02-01", 1, 1, "text", "Closed with explanation", 0, "h", "Yes"),
        (2, "2019-02-01", "2019-02-01", 1, 1, "text", "Closed with explanation", 0, "h", "Yes"),
        (3, "2019-02-01", "2019-02-01", 1, 1, "text", "Closed with explanation", 0, "h", "Yes"),
        (4, "2019-02-01", "2019-02-01", 1, 1, "text", "Closed with explanation", 0, "h", "No"),
    ]
    memory_db.executemany(
        """
        INSERT INTO fact_complaints (
            complaint_id, date_received, date_sent_to_company, product_id, company_id,
            consumer_complaint_narrative, company_response_to_consumer, reported_relief,
            narrative_group_id, timely_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        records,
    )
    memory_db.commit()

    df = execute_query(memory_db, "sql/analysis/08_timely_responses.sql")
    p1 = df[df["product_name"] == "Credit card"].iloc[0]
    assert p1["total_complaints"] == 4
    assert p1["timely_count"] == 3
    assert p1["untimely_count"] == 1
    assert p1["timely_percentage"] == 75.0


def test_product_mix_benchmark_excludes_company_with_partial_missing_peers(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Company Alpha (id 1):
    # Product 1: 120 complaints (60 relief=1, 60 relief=0)
    for _ in range(60):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(60):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "text", "Closed with explanation", 0, "h"))
        cid += 1
    # Product 2: 100 complaints (50 relief=1, 50 relief=0) - only Company Alpha has complaints here
    for _ in range(50):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(50):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "text", "Closed with explanation", 0, "h"))
        cid += 1

    # Company Beta (id 2):
    # Product 1: 200 complaints (50 relief=1, 150 relief=0)
    for _ in range(50):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "text", "Closed with monetary relief", 1, "h"))
        cid += 1
    for _ in range(150):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "text", "Closed with explanation", 0, "h"))
        cid += 1

    memory_db.executemany(
        """
        INSERT INTO fact_complaints (
            complaint_id, date_received, date_sent_to_company, product_id, company_id,
            consumer_complaint_narrative, company_response_to_consumer, reported_relief, narrative_group_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        records,
    )
    memory_db.commit()

    df = execute_query(memory_db, "sql/analysis/07_product_mix_benchmark.sql")

    # Company Alpha has 220 eligible complaints across Product 1 and Product 2,
    # but Product 2 has no peer companies. Therefore, Company Alpha must be excluded.
    assert "Company Alpha" not in df["company_name"].values

    # Company Beta only operated in Product 1 where peers exist, and has 200 complaints, so it is included.
    assert "Company Beta" in df["company_name"].values
    beta_row = df[df["company_name"] == "Company Beta"].iloc[0]
    assert beta_row["eligible_complaints"] == 200
    assert beta_row["observed_relief_percentage"] == 25.0
    assert beta_row["expected_relief_percentage"] == 50.0
    assert beta_row["diff_percentage_points"] == -25.0


def test_format_sql_findings_report_dynamic_values_and_missing_benchmark() -> None:
    def create_sample_results(top_share: float, min_relief: float, has_benchmark: bool = True) -> dict[str, pd.DataFrame]:
        monthly = pd.DataFrame([
            {"month": "2019-01", "complaint_count": 100, "prev_month_count": None, "mom_pct_change": None},
            {"month": "2019-02", "complaint_count": 120, "prev_month_count": 100, "mom_pct_change": 20.0},
        ])
        products = pd.DataFrame([
            {"product_name": "Specialty Loan", "complaint_count": 150, "percentage": top_share, "volume_rank": 1},
            {"product_name": "Retail Account", "complaint_count": 70, "percentage": round(100.0 - top_share, 2), "volume_rank": 2},
        ])
        relief = pd.DataFrame([
            {
                "product_name": "Specialty Loan",
                "total_complaints": 150,
                "eligible_complaints": 140,
                "relief_complaints": 42,
                "explanation_complaints": 98,
                "unlabeled_complaints": 10,
                "relief_percentage": 30.0,
            },
            {
                "product_name": "Retail Account",
                "total_complaints": 70,
                "eligible_complaints": 60,
                "relief_complaints": 6,
                "explanation_complaints": 54,
                "unlabeled_complaints": 10,
                "relief_percentage": min_relief,
            },
        ])
        companies = pd.DataFrame([
            {"company_name": "Corp One", "total_complaints": 100, "percentage_of_all_complaints": 45.45, "products_represented": 2},
            {"company_name": "Corp Two", "total_complaints": 70, "percentage_of_all_complaints": 31.82, "products_represented": 1},
            {"company_name": "Corp Three", "total_complaints": 50, "percentage_of_all_complaints": 22.73, "products_represented": 1},
        ])
        timely = pd.DataFrame([
            {"product_name": "Specialty Loan", "total_complaints": 150, "timely_count": 145, "untimely_count": 5, "unexpected_or_missing_count": 0, "timely_percentage": 96.67},
            {"product_name": "Retail Account", "total_complaints": 70, "timely_count": 63, "untimely_count": 7, "unexpected_or_missing_count": 0, "timely_percentage": 90.00},
        ])
        if has_benchmark:
            benchmark = pd.DataFrame([
                {
                    "company_name": "Corp Leader",
                    "eligible_complaints": 210,
                    "products_represented": 2,
                    "observed_relief_percentage": 35.0,
                    "expected_relief_percentage": 20.0,
                    "diff_percentage_points": 15.0,
                },
                {
                    "company_name": "Corp Laggard",
                    "eligible_complaints": 205,
                    "products_represented": 1,
                    "observed_relief_percentage": 10.0,
                    "expected_relief_percentage": 25.0,
                    "diff_percentage_points": -15.0,
                },
            ])
        else:
            benchmark = pd.DataFrame(columns=[
                "company_name",
                "eligible_complaints",
                "products_represented",
                "observed_relief_percentage",
                "expected_relief_percentage",
                "diff_percentage_points",
            ])

        return {
            "01_monthly_complaints.sql": monthly,
            "02_product_distribution.sql": products,
            "03_product_relief.sql": relief,
            "04_company_volume.sql": companies,
            "07_product_mix_benchmark.sql": benchmark,
            "08_timely_responses.sql": timely,
        }

    # Case 1: First set of parameters
    res1 = create_sample_results(top_share=58.25, min_relief=4.50, has_benchmark=True)
    report1 = format_sql_findings_report(res1)
    assert "Specialty Loan accounts for 58.25%" in report1
    assert "4.50% for Retail Account" in report1
    assert "Corp Leader: 35.00% observed vs. 20.00% expected" in report1
    assert "Corp Laggard: 10.00% observed vs. 25.00% expected" in report1
    assert "+15.00 percentage points" in report1
    assert "-15.00 percentage points" in report1

    # Case 2: Changing the parameters changes the generated report text dynamically
    res2 = create_sample_results(top_share=64.10, min_relief=8.20, has_benchmark=True)
    report2 = format_sql_findings_report(res2)
    assert "Specialty Loan accounts for 64.10%" in report2
    assert "58.25%" not in report2
    assert "8.20% for Retail Account" in report2
    assert "4.50%" not in report2

    # Case 3: Missing benchmark rows does not produce false comparisons or crash
    res_no_bm = create_sample_results(top_share=50.0, min_relief=5.0, has_benchmark=False)
    report_no_bm = format_sql_findings_report(res_no_bm)
    assert "Benchmark comparison is unavailable" in report_no_bm
    assert "Experian" not in report_no_bm
    assert "TransUnion" not in report_no_bm
    assert "0.00 percentage points" not in report_no_bm

