-- Top five complaint issues within each financial product for 2019.
WITH issue_counts AS (
    SELECT
        p.product_name,
        f.issue,
        COUNT(*) AS complaint_count
    FROM fact_complaints f
    JOIN dim_products p ON f.product_id = p.product_id
    WHERE f.date_received >= '2019-01-01'
      AND f.date_received < '2020-01-01'
    GROUP BY p.product_name, f.issue
),
ranked_issues AS (
    SELECT
        product_name,
        issue,
        complaint_count,
        ROUND(100.0 * complaint_count / SUM(complaint_count) OVER (PARTITION BY product_name), 2) AS percentage_of_product_complaints,
        ROW_NUMBER() OVER (PARTITION BY product_name ORDER BY complaint_count DESC) AS issue_rank
    FROM issue_counts
)
SELECT
    product_name,
    issue,
    complaint_count,
    percentage_of_product_complaints,
    issue_rank
FROM ranked_issues
WHERE issue_rank <= 5
ORDER BY product_name ASC, issue_rank ASC;

