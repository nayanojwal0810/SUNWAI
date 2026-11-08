-- Reported-relief rates within company and product combinations with >= 50 eligible complaints.
WITH company_product_summary AS (
    SELECT
        c.company_name,
        p.product_name,
        COUNT(CASE WHEN f.reported_relief IN (0, 1) THEN 1 END) AS eligible_complaints,
        COUNT(CASE WHEN f.reported_relief = 1 THEN 1 END) AS relief_count,
        ROUND(100.0 * COUNT(CASE WHEN f.reported_relief = 1 THEN 1 END) / NULLIF(COUNT(CASE WHEN f.reported_relief IN (0, 1) THEN 1 END), 0), 2) AS relief_rate
    FROM fact_complaints f
    JOIN dim_companies c ON f.company_id = c.company_id
    JOIN dim_products p ON f.product_id = p.product_id
    WHERE f.date_received >= '2019-01-01'
      AND f.date_received < '2020-01-01'
    GROUP BY c.company_name, p.product_name
    HAVING eligible_complaints >= 50
)
SELECT
    company_name,
    product_name,
    eligible_complaints,
    relief_count,
    relief_rate,
    DENSE_RANK() OVER (PARTITION BY product_name ORDER BY relief_rate DESC) AS rank_in_product
FROM company_product_summary
ORDER BY product_name ASC, relief_rate DESC;

