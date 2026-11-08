-- SUNWAI Relational Database Schema
-- Defines dimension and fact tables for CFPB consumer complaints.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_complaints (
    complaint_id INTEGER PRIMARY KEY,
    date_received TEXT NOT NULL,
    date_sent_to_company TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    state_id INTEGER,
    sub_product TEXT,
    issue TEXT,
    sub_issue TEXT,
    consumer_complaint_narrative TEXT NOT NULL,
    company_public_response TEXT,
    zip_code TEXT,
    tags TEXT,
    consumer_consent_provided TEXT,
    submitted_via TEXT,
    company_response_to_consumer TEXT NOT NULL,
    timely_response TEXT,
    reported_relief INTEGER,
    narrative_group_id TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES dim_products (product_id),
    FOREIGN KEY (company_id) REFERENCES dim_companies (company_id),
    FOREIGN KEY (state_id) REFERENCES dim_states (state_id),
    CHECK (reported_relief IN (0, 1) OR reported_relief IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_fact_complaints_date_received
    ON fact_complaints (date_received);

CREATE INDEX IF NOT EXISTS idx_fact_complaints_product_id
    ON fact_complaints (product_id);

CREATE INDEX IF NOT EXISTS idx_fact_complaints_company_id
    ON fact_complaints (company_id);

CREATE INDEX IF NOT EXISTS idx_fact_complaints_reported_relief
    ON fact_complaints (reported_relief);

