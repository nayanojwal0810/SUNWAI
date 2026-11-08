"""Build SQLite database from prepared complaint dataset."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd

from src.data.profile_complaints import load_config


def to_sql_value(val: Any) -> Any:
    """Convert pandas/numpy values to Python types compatible with sqlite3 NULLs."""
    if pd.isna(val):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


def init_database(conn: sqlite3.Connection, schema_path: str | Path = "sql/schema.sql") -> None:
    """Initialize database tables and indexes from the SQL schema file."""
    path = Path(schema_path)
    if not path.is_file():
        raise FileNotFoundError(f"Schema file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(schema_sql)
    conn.commit()


def populate_dimensions(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Populate dim_products, dim_companies, and dim_states with sorted distinct values."""
    cursor = conn.cursor()

    # 1. Products
    products = sorted(df["product"].dropna().unique())
    cursor.executemany(
        "INSERT INTO dim_products (product_name) VALUES (?);",
        [(p,) for p in products],
    )
    cursor.execute("SELECT product_name, product_id FROM dim_products;")
    product_map = {name: pid for name, pid in cursor.fetchall()}

    # 2. Companies
    companies = sorted(df["company"].dropna().unique())
    cursor.executemany(
        "INSERT INTO dim_companies (company_name) VALUES (?);",
        [(c,) for c in companies],
    )
    cursor.execute("SELECT company_name, company_id FROM dim_companies;")
    company_map = {name: cid for name, cid in cursor.fetchall()}

    # 3. States (non-missing only)
    states = sorted(df["state"].dropna().unique())
    cursor.executemany(
        "INSERT INTO dim_states (state_code) VALUES (?);",
        [(s,) for s in states],
    )
    cursor.execute("SELECT state_code, state_id FROM dim_states;")
    state_map = {code: sid for code, sid in cursor.fetchall()}

    conn.commit()
    return product_map, company_map, state_map


def populate_fact_complaints(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    product_map: dict[str, int],
    company_map: dict[str, int],
    state_map: dict[str, int],
    batch_size: int = 5000,
) -> int:
    """Insert complaints into fact_complaints in batches using mapped foreign keys."""
    # Prepare aligned DataFrame with exact column order matching fact_complaints schema
    fact_df = pd.DataFrame(
        {
            "complaint_id": df["complaint_id"].astype("int64"),
            "date_received": df["date_received"],
            "date_sent_to_company": df["date_sent_to_company"],
            "product_id": df["product"].map(product_map),
            "company_id": df["company"].map(company_map),
            "state_id": df["state"].map(state_map),
            "sub_product": df["sub_product"],
            "issue": df["issue"],
            "sub_issue": df["sub_issue"],
            "consumer_complaint_narrative": df["consumer_complaint_narrative"],
            "company_public_response": df["company_public_response"],
            "zip_code": df["zip_code"].astype(str).replace("nan", pd.NA),
            "tags": df["tags"],
            "consumer_consent_provided": df["consumer_consent_provided"],
            "submitted_via": df["submitted_via"],
            "company_response_to_consumer": df["company_response_to_consumer"],
            "timely_response": df["timely_response"],
            "reported_relief": df["reported_relief"],
            "narrative_group_id": df["narrative_group_id"],
        }
    )

    insert_sql = """
    INSERT INTO fact_complaints (
        complaint_id,
        date_received,
        date_sent_to_company,
        product_id,
        company_id,
        state_id,
        sub_product,
        issue,
        sub_issue,
        consumer_complaint_narrative,
        company_public_response,
        zip_code,
        tags,
        consumer_consent_provided,
        submitted_via,
        company_response_to_consumer,
        timely_response,
        reported_relief,
        narrative_group_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    cursor = conn.cursor()
    total_rows = len(fact_df)
    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        chunk = fact_df.iloc[start_idx:end_idx]
        records = [
            tuple(to_sql_value(v) for v in row)
            for row in chunk.itertuples(index=False)
        ]
        cursor.executemany(insert_sql, records)

    conn.commit()
    return total_rows


def validate_database(conn: sqlite3.Connection, df: pd.DataFrame) -> dict[str, Any]:
    """Perform thorough consistency checks between the prepared DataFrame and SQLite tables."""
    cursor = conn.cursor()

    # 1. Foreign key integrity
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    if fk_violations:
        raise ValueError(f"Foreign key violations detected: {fk_violations}")

    # 2. Record count in fact table
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT complaint_id) FROM fact_complaints;")
    fact_count, distinct_ids = cursor.fetchone()
    if fact_count != len(df):
        raise ValueError(f"Fact count mismatch: database has {fact_count:,}, expected {len(df):,}.")
    if distinct_ids != len(df):
        raise ValueError(f"Duplicate complaint IDs found in database: {fact_count - distinct_ids}.")

    # 3. Dimension table counts
    cursor.execute("SELECT COUNT(*) FROM dim_products;")
    db_product_count = cursor.fetchone()[0]
    expected_product_count = int(df["product"].nunique())
    if db_product_count != expected_product_count:
        raise ValueError(f"Product count mismatch: DB={db_product_count}, CSV={expected_product_count}.")

    cursor.execute("SELECT COUNT(*) FROM dim_companies;")
    db_company_count = cursor.fetchone()[0]
    expected_company_count = int(df["company"].nunique())
    if db_company_count != expected_company_count:
        raise ValueError(f"Company count mismatch: DB={db_company_count}, CSV={expected_company_count}.")

    cursor.execute("SELECT COUNT(*) FROM dim_states;")
    db_state_count = cursor.fetchone()[0]
    expected_state_count = int(df["state"].dropna().nunique())
    if db_state_count != expected_state_count:
        raise ValueError(f"State count mismatch: DB={db_state_count}, CSV={expected_state_count}.")

    # 4. Null state handling
    cursor.execute("SELECT COUNT(*) FROM fact_complaints WHERE state_id IS NULL;")
    db_null_states = cursor.fetchone()[0]
    expected_null_states = int(df["state"].isna().sum())
    if db_null_states != expected_null_states:
        raise ValueError(f"Null state mismatch: DB={db_null_states}, CSV={expected_null_states}.")

    # 5. Reported relief counts
    cursor.execute("""
        SELECT
            SUM(CASE WHEN reported_relief = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN reported_relief = 0 THEN 1 ELSE 0 END),
            SUM(CASE WHEN reported_relief IS NULL THEN 1 ELSE 0 END)
        FROM fact_complaints;
    """)
    db_relief_1, db_relief_0, db_relief_null = cursor.fetchone()

    expected_relief_1 = int((df["reported_relief"] == 1).sum())
    expected_relief_0 = int((df["reported_relief"] == 0).sum())
    expected_relief_null = int(df["reported_relief"].isna().sum())

    if (db_relief_1, db_relief_0, db_relief_null) != (expected_relief_1, expected_relief_0, expected_relief_null):
        raise ValueError(
            f"Relief distribution mismatch:\n"
            f"DB: (1={db_relief_1}, 0={db_relief_0}, NULL={db_relief_null})\n"
            f"CSV: (1={expected_relief_1}, 0={expected_relief_0}, NULL={expected_relief_null})"
        )

    # 6. Product distribution join test
    cursor.execute("""
        SELECT p.product_name, COUNT(*)
        FROM fact_complaints f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.product_name;
    """)
    db_product_dist = dict(cursor.fetchall())
    expected_product_dist = df["product"].value_counts().to_dict()
    if db_product_dist != expected_product_dist:
        raise ValueError("Product distribution joined counts do not match CSV.")

    # 7. Non-empty narratives count
    cursor.execute("SELECT COUNT(*) FROM fact_complaints WHERE length(trim(consumer_complaint_narrative)) > 0;")
    db_narrative_count = cursor.fetchone()[0]
    if db_narrative_count != len(df):
        raise ValueError(f"Narrative count mismatch: DB={db_narrative_count}, expected={len(df)}.")

    return {
        "complaints_count": fact_count,
        "products_count": db_product_count,
        "companies_count": db_company_count,
        "states_count": db_state_count,
        "null_states_count": db_null_states,
        "relief_distribution": {
            "relief_1": db_relief_1,
            "relief_0": db_relief_0,
            "relief_null": db_relief_null,
        },
    }


def build_database(
    config_path: str | Path = "config/settings.yaml",
    schema_path: str | Path = "sql/schema.sql",
) -> dict[str, Any]:
    """Build SQLite database from prepared dataset using an atomic, safe rebuild process."""
    config = load_config(config_path)
    clean_file = config.get("data", {}).get("clean_file", "data/processed/complaints_clean.csv.gz")
    db_file = config.get("data", {}).get("database_file", "data/processed/sunwai.sqlite3")

    clean_path = Path(clean_file)
    if not clean_path.is_file():
        raise FileNotFoundError(f"Prepared dataset not found: {clean_path}")

    final_db_path = Path(db_file)
    final_db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_db_path = final_db_path.parent / f"{final_db_path.stem}_temp{final_db_path.suffix}"

    if temp_db_path.exists():
        temp_db_path.unlink()

    df = pd.read_csv(clean_path, low_memory=False)

    conn = sqlite3.connect(temp_db_path)
    try:
        init_database(conn, schema_path)
        product_map, company_map, state_map = populate_dimensions(conn, df)
        populate_fact_complaints(conn, df, product_map, company_map, state_map)
        validation_results = validate_database(conn, df)
    except Exception:
        conn.close()
        if temp_db_path.exists():
            temp_db_path.unlink()
        raise
    else:
        conn.close()
        os.replace(temp_db_path, final_db_path)

    return {
        "complaints": validation_results["complaints_count"],
        "tables": 4,
        "database_file": str(final_db_path).replace("\\", "/"),
        "validation": validation_results,
    }


def main() -> None:
    """Entry point to build database and output brief summary."""
    results = build_database()
    print("Database created successfully.")
    print(f"Complaints: {results['complaints']:,}")
    print(f"Tables: {results['tables']}")
    print(f"Database: {results['database_file']}")


if __name__ == "__main__":
    main()

