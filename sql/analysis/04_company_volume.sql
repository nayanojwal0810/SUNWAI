-- Top 15 companies by complaint volume and product breadth in 2019.
WITH company_summary AS (
    SELECT
        c.company_name,
        COUNT(*) AS total_complaints,
        COUNT(DISTINCT f.product_id) AS products_represented
    FROM fact_complaints f
    JOIN dim_companies c ON f.company_id = c.company_id
    WHERE f.date_received >= '2019-01-01'
      AND f.date_received < '2020-01-01'
    GROUP BY c.company_name
)
SELECT
    company_name,
    total_complaints,
    ROUND(100.0 * total_complaints / (
        SELECT COUNT(*)
        FROM fact_complaints
        WHERE date_received >= '2019-01-01'
          AND date_received < '2020-01-01'
    ), 2) AS percentage_of_all_complaints,
    products_represented
FROM company_summary
ORDER BY total_complaints DESC
LIMIT 15;

