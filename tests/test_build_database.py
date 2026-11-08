"""Unit tests for SQLite database initialization, loading, and validation."""

from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from src.data.build_database import (
    init_database,
    populate_dimensions,
    populate_fact_complaints,
    validate_database,
)


@pytest.fixture
def sample_complaints_df() -> pd.DataFrame:
    """Create a minimal synthetic complaints DataFrame for testing."""
    return pd.DataFrame(
        {
            "complaint_id": [101, 102, 103],
            "date_received": ["2019-03-01", "2019-03-02", "2019-03-03"],
            "date_sent_to_company": ["2019-03-01", "2019-03-02", "2019-03-03"],
            "product": ["Credit card", "Mortgage", "Credit card"],
            "sub_product": ["General", "Fixed", "General"],
            "issue": ["Billing", "Interest", "Billing"],
            "sub_issue": ["Late fee", "Rate error", None],
            "consumer_complaint_narrative": ["Narrative 1", "Narrative 2", "Narrative 3"],
            "company_public_response": [None, "Public reply", None],
            "company": ["Alpha Bank", "Beta Finance", "Alpha Bank"],
            "state": ["CA", None, "NY"],
            "zip_code": ["012XX", "902XX", "100XX"],
            "tags": [None, "Servicemember", None],
            "consumer_consent_provided": ["Consent provided"] * 3,
            "submitted_via": ["Web"] * 3,
            "company_response_to_consumer": [
                "Closed with explanation",
                "Closed with monetary relief",
                "Untimely response",
            ],
            "timely_response": ["Yes", "Yes", "No"],
            "reported_relief": pd.Series([0, 1, pd.NA], dtype="Int64"),
            "narrative_group_id": ["hash_1", "hash_2", "hash_3"],
        }
    )


def test_init_database_creates_tables_and_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    conn = sqlite3.connect(db_path)
    init_database(conn, "sql/schema.sql")

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cursor.fetchall()}
    assert {"dim_products", "dim_companies", "dim_states", "fact_complaints"}.issubset(tables)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
    indexes = {r[0] for r in cursor.fetchall()}
    expected_indexes = {
        "idx_fact_complaints_date_received",
        "idx_fact_complaints_product_id",
        "idx_fact_complaints_company_id",
        "idx_fact_complaints_reported_relief",
    }
    assert expected_indexes.issubset(indexes)
    conn.close()


def test_populate_and_validate_database(tmp_path: Path, sample_complaints_df: pd.DataFrame) -> None:
    db_path = tmp_path / "test.sqlite3"
    conn = sqlite3.connect(db_path)
    init_database(conn, "sql/schema.sql")

    p_map, c_map, s_map = populate_dimensions(conn, sample_complaints_df)
    assert len(p_map) == 2  # Credit card, Mortgage
    assert len(c_map) == 2  # Alpha Bank, Beta Finance
    assert len(s_map) == 2  # CA, NY (None excluded)

    rows_inserted = populate_fact_complaints(conn, sample_complaints_df, p_map, c_map, s_map)
    assert rows_inserted == 3

    validation = validate_database(conn, sample_complaints_df)
    assert validation["complaints_count"] == 3
    assert validation["null_states_count"] == 1
    assert validation["relief_distribution"]["relief_1"] == 1
    assert validation["relief_distribution"]["relief_0"] == 1
    assert validation["relief_distribution"]["relief_null"] == 1

    cursor = conn.cursor()
    cursor.execute("SELECT zip_code, state_id, reported_relief FROM fact_complaints WHERE complaint_id = 101;")
    zip_code, state_id, relief = cursor.fetchone()
    assert zip_code == "012XX"  # Leading zero preserved
    assert state_id is not None
    assert relief == 0

    # Complaint 102 has missing state
    cursor.execute("SELECT state_id, reported_relief FROM fact_complaints WHERE complaint_id = 102;")
    state_id_102, relief_102 = cursor.fetchone()
    assert state_id_102 is None
    assert relief_102 == 1

    # Complaint 103 has null relief
    cursor.execute("SELECT reported_relief FROM fact_complaints WHERE complaint_id = 103;")
    assert cursor.fetchone()[0] is None
    conn.close()


def test_foreign_key_enforcement(tmp_path: Path) -> None:
    db_path = tmp_path / "test_fk.sqlite3"
    conn = sqlite3.connect(db_path)
    init_database(conn, "sql/schema.sql")

    cursor = conn.cursor()
    cursor.execute("INSERT INTO dim_products (product_name) VALUES ('Debt collection');")
    cursor.execute("INSERT INTO dim_companies (company_name) VALUES ('Test Corp');")
    conn.commit()

    # Attempt to insert complaint with nonexistent product_id (999)
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO fact_complaints (
                complaint_id, date_received, date_sent_to_company, product_id, company_id,
                consumer_complaint_narrative, company_response_to_consumer, narrative_group_id
            ) VALUES (1, '2019-01-01', '2019-01-01', 999, 1, 'Narrative', 'Closed with explanation', 'h1');
        """)
    conn.close()


def test_reported_relief_check_constraint(tmp_path: Path) -> None:
    db_path = tmp_path / "test_check.sqlite3"
    conn = sqlite3.connect(db_path)
    init_database(conn, "sql/schema.sql")

    cursor = conn.cursor()
    cursor.execute("INSERT INTO dim_products (product_name) VALUES ('Debt collection');")
    cursor.execute("INSERT INTO dim_companies (company_name) VALUES ('Test Corp');")
    conn.commit()

    # Attempt to insert invalid reported_relief value (2)
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO fact_complaints (
                complaint_id, date_received, date_sent_to_company, product_id, company_id,
                consumer_complaint_narrative, company_response_to_consumer, reported_relief,
                narrative_group_id
            ) VALUES (1, '2019-01-01', '2019-01-01', 1, 1, 'Narrative', 'Closed with explanation', 2, 'h1');
        """)
    conn.close()


def test_rebuild_does_not_duplicate_records(tmp_path: Path, sample_complaints_df: pd.DataFrame) -> None:
    db_path = tmp_path / "rebuild_test.sqlite3"

    for _ in range(2):
        conn = sqlite3.connect(db_path)
        # Drop existing tables to simulate clean rebuild
        conn.execute("DROP TABLE IF EXISTS fact_complaints;")
        conn.execute("DROP TABLE IF EXISTS dim_products;")
        conn.execute("DROP TABLE IF EXISTS dim_companies;")
        conn.execute("DROP TABLE IF EXISTS dim_states;")
        init_database(conn, "sql/schema.sql")
        p_map, c_map, s_map = populate_dimensions(conn, sample_complaints_df)
        populate_fact_complaints(conn, sample_complaints_df, p_map, c_map, s_map)
        validation = validate_database(conn, sample_complaints_df)
        conn.close()
        assert validation["complaints_count"] == 3

