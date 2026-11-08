"""Unit tests for business exploratory data analysis and statistical validation."""

import sqlite3

import numpy as np
import pandas as pd
import pytest

from src.analytics.analyze_business import (
    audit_company_benchmark,
    calculate_wilson_interval,
    compute_company_benchmark,
    compute_product_period_sensitivity,
    compute_product_relief_intervals,
    perform_chi_square_test,
)


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


def test_wilson_interval_calculations_and_zero_complaints() -> None:
    # Zero complaints case
    low_zero, high_zero = calculate_wilson_interval(0, 0)
    assert low_zero is None
    assert high_zero is None

    # Invalid cases (x > n, negative)
    assert calculate_wilson_interval(-5, 0) == (None, None)
    assert calculate_wilson_interval(10, 15) == (None, None)

    # Known hand-calculated case: n=100, x=50, p=0.5
    low, high = calculate_wilson_interval(100, 50)
    assert low == 40.38
    assert high == 59.62

    # Edge cases at boundary
    low_0, high_0 = calculate_wilson_interval(10, 0)
    assert low_0 == 0.0
    assert high_0 > 0.0

    low_10, high_10 = calculate_wilson_interval(10, 10)
    assert low_10 < 100.0
    assert high_10 == 100.0


def test_compute_product_relief_intervals_dataframe() -> None:
    df = pd.DataFrame([
        {"product_name": "Credit card", "eligible_complaints": 100, "relief_complaints": 50, "relief_percentage": 50.0},
        {"product_name": "Mortgage", "eligible_complaints": 0, "relief_complaints": 0, "relief_percentage": 0.0},
    ])
    res = compute_product_relief_intervals(df)
    assert len(res) == 2
    assert res.loc[0, "ci_lower"] == 40.38
    assert res.loc[0, "ci_upper"] == 59.62
    assert res.loc[0, "ci_width"] == 19.24
    assert pd.isna(res.loc[1, "ci_lower"])
    assert pd.isna(res.loc[1, "ci_width"])


def test_chi_square_and_cramers_v_calculation() -> None:
    # 2x2 balanced contingency table:
    # Product A: 20 relief, 80 explanation
    # Product B: 80 relief, 20 explanation
    df = pd.DataFrame([
        {"product_name": "Product A", "relief_complaints": 20, "explanation_complaints": 80},
        {"product_name": "Product B", "relief_complaints": 80, "explanation_complaints": 20},
    ])
    result = perform_chi_square_test(df)
    # chi2_contingency applies Yates' correction on 2x2 tables: 4 * (29.5^2 / 50) = 69.62
    assert pytest.approx(result["chi2_stat"], abs=0.1) == 69.62
    assert result["dof"] == 1
    assert result["total_observations"] == 200
    assert result["p_value"] < 0.0001
    # Cramér's V: sqrt(69.62 / 200) = 0.5900
    assert pytest.approx(result["cramers_v"], abs=0.001) == 0.5900


def test_relief_denominator_excludes_unlabeled(memory_db: sqlite3.Connection) -> None:
    records = [
        # 10 complaints with relief=1
        *[(i, "2019-05-01", "2019-05-01", 1, 1, "text", "Closed with monetary relief", 1, "h") for i in range(1, 11)],
        # 30 complaints with relief=0
        *[(i, "2019-05-01", "2019-05-01", 1, 1, "text", "Closed with explanation", 0, "h") for i in range(11, 41)],
        # 10 complaints with relief=None (unlabeled)
        *[(i, "2019-05-01", "2019-05-01", 1, 1, "text", "Untimely response", None, "h") for i in range(41, 51)],
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

    fy_relief = pd.DataFrame([
        {"product_name": "Credit card", "eligible_complaints": 40, "relief_percentage": 25.0}
    ])
    sens = compute_product_period_sensitivity(memory_db, fy_relief)
    row = sens.iloc[0]
    # Denominator must exclude the 10 unlabeled complaints -> exactly 40 eligible
    assert row["eligible_complaints_jan_oct"] == 40
    assert row["relief_percentage_jan_oct"] == 25.0
    assert row["diff_percentage_points"] == 0.0


def test_hand_calculated_two_product_benchmark(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Company Alpha (id 1):
    # Product 1: 100 eligible, 40 relief (40%)
    for _ in range(40):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "r", 1, "h"))
        cid += 1
    for _ in range(60):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "e", 0, "h"))
        cid += 1
    # Product 2: 100 eligible, 20 relief (20%)
    for _ in range(20):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "t", "r", 1, "h"))
        cid += 1
    for _ in range(80):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "t", "e", 0, "h"))
        cid += 1
    # Total Alpha: 200 eligible, 60 relief -> observed rate = 30.0%

    # Company Beta (id 2):
    # Product 1: 200 eligible, 20 relief -> peer rate = 20 / 200 = 10.0%
    for _ in range(20):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "r", 1, "h"))
        cid += 1
    for _ in range(180):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "e", 0, "h"))
        cid += 1
    # Product 2: 200 eligible, 80 relief -> peer rate = 80 / 200 = 40.0%
    for _ in range(80):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 2, "t", "r", 1, "h"))
        cid += 1
    for _ in range(120):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 2, "t", "e", 0, "h"))
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

    df = compute_company_benchmark(memory_db, "2019-01-01", "2020-01-01", 200, 1)
    alpha = df[df["company_name"] == "Company Alpha"].iloc[0]
    assert alpha["eligible_complaints"] == 200
    assert alpha["observed_relief_percentage"] == 30.0
    # Expected: (100 * 0.10 + 100 * 0.40) / 200 = 50 / 200 = 25.0%
    assert alpha["expected_relief_percentage"] == 25.0
    assert alpha["diff_percentage_points"] == 5.0


def test_company_excluded_when_lacking_peer_in_one_product(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Company Alpha (id 1):
    # Product 1: 150 eligible complaints
    for _ in range(150):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "Closed with explanation", 0, "h"))
        cid += 1
    # Product 2: 60 eligible complaints (only Company Alpha operates here)
    for _ in range(60):
        records.append((cid, "2019-05-01", "2019-05-01", 2, 1, "t", "Closed with explanation", 0, "h"))
        cid += 1

    # Company Beta (id 2):
    # Product 1: 200 eligible complaints (peer for Alpha in Product 1)
    for _ in range(200):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "Closed with explanation", 0, "h"))
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

    df = compute_company_benchmark(memory_db, "2019-01-01", "2020-01-01", 200, 1)
    # Company Alpha has 210 eligible complaints but 0 peers in Product 2 -> must be excluded
    assert "Company Alpha" not in df["company_name"].values
    # Company Beta operates only in Product 1 where peers exist -> included
    assert "Company Beta" in df["company_name"].values


def test_stricter_peer_support_filtering(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Company Alpha (id 1): Product 1: 200 complaints
    for _ in range(200):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "Closed with explanation", 0, "h"))
        cid += 1

    # Company Beta (id 2): Product 1: 10 complaints (peer for Alpha, but < 20)
    for _ in range(10):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "Closed with explanation", 0, "h"))
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

    # Rule 1: min_peer_eligible = 1 -> Alpha qualifies (10 >= 1)
    df_lenient = compute_company_benchmark(memory_db, "2019-01-01", "2020-01-01", 200, min_peer_eligible=1)
    assert "Company Alpha" in df_lenient["company_name"].values

    # Rule 2: min_peer_eligible = 20 -> Alpha excluded (10 < 20)
    df_strict = compute_company_benchmark(memory_db, "2019-01-01", "2020-01-01", 200, min_peer_eligible=20)
    assert "Company Alpha" not in df_strict["company_name"].values


def test_period_sensitivity_date_filtering(memory_db: sqlite3.Connection) -> None:
    records = [
        # Product 1: 10 complaints in May 2019 (both FY and Jan-Oct)
        *[(i, "2019-05-15", "2019-05-15", 1, 1, "t", "Closed with monetary relief", 1, "h") for i in range(1, 11)],
        # Product 1: 10 complaints in November 2019 (only in FY)
        *[(i, "2019-11-15", "2019-11-15", 1, 1, "t", "Closed with explanation", 0, "h") for i in range(11, 21)],
        # Product 1: 5 complaints in January 2020 (excluded from both!)
        *[(i, "2020-01-05", "2020-01-05", 1, 1, "t", "Closed with monetary relief", 1, "h") for i in range(21, 26)],
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

    fy_df = pd.DataFrame([
        {"product_name": "Credit card", "eligible_complaints": 20, "relief_percentage": 50.0}
    ])
    sens = compute_product_period_sensitivity(memory_db, fy_df)
    row = sens.iloc[0]

    # In Jan-Oct, only the 10 May complaints are present (100% relief)
    assert row["eligible_complaints_jan_oct"] == 10
    assert row["relief_percentage_jan_oct"] == 100.0

    # Full year had 20 eligible complaints and 50% relief
    assert row["eligible_complaints_full_year"] == 20
    assert row["relief_percentage_full_year"] == 50.0

    # Difference: 50.0 - 100.0 = -50.0 pp
    assert row["diff_percentage_points"] == -50.0
    assert row["abs_diff_pp"] == 50.0


def test_audit_company_benchmark_detects_rate_mismatch(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Company Alpha (id 1): 200 complaints in Product 1 (40 relief=1, 160 relief=0 -> obs = 20.0%)
    for _ in range(40):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "r", 1, "h"))
        cid += 1
    for _ in range(160):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "e", 0, "h"))
        cid += 1

    # Company Beta (id 2): 200 complaints in Product 1 (100 relief=1, 100 relief=0 -> peer rate for Alpha = 50.0%)
    # Alpha expected = 50.0%, observed = 20.0%, diff = -30.0%
    for _ in range(100):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "r", 1, "h"))
        cid += 1
    for _ in range(100):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "e", 0, "h"))
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

    # Fake SQL benchmark with matching adjusted gap (-30.0 pp) but DIFFERENT observed and expected rates!
    # Real Python: obs=20.0, exp=50.0, diff=-30.0
    # Fake SQL:    obs=30.0, exp=60.0, diff=-30.0
    fake_sql_df = pd.DataFrame([
        {
            "company_name": "Company Alpha",
            "eligible_complaints": 200,
            "products_represented": 1,
            "observed_relief_percentage": 30.0,  # mismatch: 30 vs 20
            "expected_relief_percentage": 60.0,  # mismatch: 60 vs 50
            "diff_percentage_points": -30.0,     # matches!
        },
        {
            "company_name": "Company Beta",
            "eligible_complaints": 200,
            "products_represented": 1,
            "observed_relief_percentage": 50.0,
            "expected_relief_percentage": 20.0,
            "diff_percentage_points": 30.0,
        },
    ])

    with pytest.raises(ValueError, match="exceeds 0.02 pp threshold"):
        audit_company_benchmark(memory_db, fake_sql_df)


def test_audit_company_benchmark_detects_company_set_mismatch(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    # Company Alpha (200 records in Product 1)
    for _ in range(200):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "e", 0, "h"))
        cid += 1
    # Company Beta (200 records in Product 1)
    for _ in range(200):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "e", 0, "h"))
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

    # Fake SQL with different company name
    fake_sql_df = pd.DataFrame([
        {
            "company_name": "Company Alpha",
            "eligible_complaints": 200,
            "products_represented": 1,
            "observed_relief_percentage": 0.0,
            "expected_relief_percentage": 0.0,
            "diff_percentage_points": 0.0,
        },
        {
            "company_name": "Company Different",
            "eligible_complaints": 200,
            "products_represented": 1,
            "observed_relief_percentage": 0.0,
            "expected_relief_percentage": 0.0,
            "diff_percentage_points": 0.0,
        },
    ])

    with pytest.raises(ValueError, match="Company set mismatch"):
        audit_company_benchmark(memory_db, fake_sql_df)


def test_audit_company_benchmark_detects_eligible_complaints_mismatch(memory_db: sqlite3.Connection) -> None:
    records = []
    cid = 1
    for _ in range(200):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 1, "t", "e", 0, "h"))
        cid += 1
    for _ in range(200):
        records.append((cid, "2019-05-01", "2019-05-01", 1, 2, "t", "e", 0, "h"))
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

    fake_sql_df = pd.DataFrame([
        {
            "company_name": "Company Alpha",
            "eligible_complaints": 205,  # Real is 200
            "products_represented": 1,
            "observed_relief_percentage": 0.0,
            "expected_relief_percentage": 0.0,
            "diff_percentage_points": 0.0,
        },
        {
            "company_name": "Company Beta",
            "eligible_complaints": 200,
            "products_represented": 1,
            "observed_relief_percentage": 0.0,
            "expected_relief_percentage": 0.0,
            "diff_percentage_points": 0.0,
        },
    ])

    with pytest.raises(ValueError, match="Eligible complaint count mismatch"):
        audit_company_benchmark(memory_db, fake_sql_df)

