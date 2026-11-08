# Relational Database Schema

The SUNWAI database organizes cleaned CFPB complaint records into a SQLite relational schema. It separates high-cardinality entities (products, companies, and states) into dimension tables and stores individual complaint events in a central fact table.

## Database Tables

| Table Name | Type | Description | Primary Key | Row Count |
| :--- | :--- | :--- | :--- | :---: |
| `dim_products` | Dimension | Distinct financial product categories | `product_id` | 9 |
| `dim_companies` | Dimension | Distinct financial institution names | `company_id` | 2,541 |
| `dim_states` | Dimension | Distinct US state and territory postal codes | `state_id` | 58 |
| `fact_complaints` | Fact | Individual complaint events and outcomes | `complaint_id` | 117,214 |

## Key Relationships

```
dim_products (product_id) <----+
                                |
dim_companies (company_id) <----+--- fact_complaints (product_id, company_id, state_id)
                                |
dim_states (state_id) <---------+
```

- **`fact_complaints.product_id`:** References `dim_products.product_id` (required).
- **`fact_complaints.company_id`:** References `dim_companies.company_id` (required).
- **`fact_complaints.state_id`:** References `dim_states.state_id` (nullable). Complaints with missing location data retain `NULL`.

## Data Types and Constraints

- **Foreign key enforcement:** `PRAGMA foreign_keys = ON;` ensures every complaint links to existing product and company records.
- **Relief outcome constraint:** `reported_relief` includes a CHECK constraint allowing only `0` (closed with explanation), `1` (relief granted), or `NULL` (untimely response).
- **Date formatting:** Dates are stored as ISO text strings (`YYYY-MM-DD`), allowing SQLite date functions to group complaints by month or year.
- **Location codes:** ZIP codes are stored as text (e.g., `'012XX'`) to preserve leading zeros.
- **Missing values:** Optional omitted fields (such as missing states or company public responses) are stored as native SQL `NULL`.

## Building the Database

To create or rebuild the SQLite database from the prepared dataset, run:

```bash
python -m src.data.build_database
```

The script builds the database using a temporary file and replaces `data/processed/sunwai.sqlite3` only after foreign key and consistency checks pass.

