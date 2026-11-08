# Database guide

SUNWAI stores the cleaned complaint data in SQLite so SQL queries can compare products, companies, and responses.

The database file is data/processed/sunwai.sqlite3.

## Tables

| Table | Rows | What it contains |
| --- | ---: | --- |
| fact_complaints | 117,214 | One row for each complaint |
| dim_products | 9 | Product names and their IDs |
| dim_companies | 2,541 | Company names and their IDs |
| dim_states | 58 | State and territory codes |

The complaint table stores a product_id, company_id, and state_id instead of repeating those names. SQL joins connect them to the three smaller tables.

Each complaint has a unique complaint_id. Product and company IDs must match an existing row in their tables. A missing state is allowed.

## How to use it

For example, this query counts complaints by product:

    SELECT p.product_name, COUNT(*) AS complaints
    FROM fact_complaints f
    JOIN dim_products p ON f.product_id = p.product_id
    GROUP BY p.product_name
    ORDER BY complaints DESC;

Dates are stored as YYYY-MM-DD text. ZIP codes are stored as text so leading zeros are not lost. reported_relief is 1, 0, or NULL; NULL is excluded when calculating relief rates.

## Build the database

Run this after preparing the cleaned dataset:

    python -m src.data.build_database

The script checks row counts and table links before replacing the local database file. The SQL queries used for the analysis are in sql/analysis/.
