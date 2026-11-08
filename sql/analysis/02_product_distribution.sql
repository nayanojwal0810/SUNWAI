-- Distribution of complaints by financial product across calendar year 2019.
WITH product_counts AS (
    SELECT
        p.product_name,
        COUNT(*) AS complaint_count
    FROM fact_complaints f
    JOIN dim_products p ON f.product_id = p.product_id
    WHERE f.date_received >= '2019-01-01'
      AND f.date_received < '2020-01-01'
    GROUP BY p.product_name
)
SELECT
    product_name,
    complaint_count,
    ROUND(100.0 * complaint_count / SUM(complaint_count) OVER (), 2) AS percentage,
    ROW_NUMBER() OVER (ORDER BY complaint_count DESC) AS volume_rank
FROM product_counts
ORDER BY volume_rank ASC;

