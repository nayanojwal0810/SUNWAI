-- Product-mix adjusted relief benchmark for companies with >= 200 eligible complaints in 2019.
WITH base_complaints AS (
    SELECT
        f.company_id,
        f.product_id,
        f.reported_relief
    FROM fact_complaints f
    WHERE f.date_received >= '2019-01-01'
      AND f.date_received < '2020-01-01'
      AND f.reported_relief IN (0, 1)
),
company_product_totals AS (
    SELECT
        company_id,
        product_id,
        COUNT(*) AS cp_eligible,
        SUM(reported_relief) AS cp_relief
    FROM base_complaints
    GROUP BY company_id, product_id
),
overall_product_totals AS (
    SELECT
        product_id,
        COUNT(*) AS total_product_eligible,
        SUM(reported_relief) AS total_product_relief
    FROM base_complaints
    GROUP BY product_id
),
company_product_benchmarks AS (
    SELECT
        cp.company_id,
        cp.product_id,
        cp.cp_eligible,
        cp.cp_relief,
        (op.total_product_eligible - cp.cp_eligible) AS peer_eligible,
        (op.total_product_relief - cp.cp_relief) AS peer_relief,
        CASE
            WHEN (op.total_product_eligible - cp.cp_eligible) > 0
            THEN 1.0 * (op.total_product_relief - cp.cp_relief) / (op.total_product_eligible - cp.cp_eligible)
            ELSE NULL
        END AS peer_relief_rate
    FROM company_product_totals cp
    JOIN overall_product_totals op ON cp.product_id = op.product_id
),
company_aggregates AS (
    SELECT
        cpb.company_id,
        COUNT(DISTINCT cpb.product_id) AS products_represented,
        SUM(cpb.cp_eligible) AS eligible_complaints,
        SUM(cpb.cp_relief) AS observed_relief_count,
        SUM(cpb.cp_eligible * cpb.peer_relief_rate) AS expected_relief_count
    FROM company_product_benchmarks cpb
    GROUP BY cpb.company_id
    HAVING eligible_complaints >= 200
       AND COUNT(CASE WHEN cpb.peer_relief_rate IS NULL THEN 1 END) = 0
)
SELECT
    c.company_name,
    ca.eligible_complaints,
    ca.products_represented,
    ROUND(100.0 * ca.observed_relief_count / ca.eligible_complaints, 2) AS observed_relief_percentage,
    ROUND(100.0 * ca.expected_relief_count / ca.eligible_complaints, 2) AS expected_relief_percentage,
    ROUND(100.0 * (ca.observed_relief_count - ca.expected_relief_count) / ca.eligible_complaints, 2) AS diff_percentage_points
FROM company_aggregates ca
JOIN dim_companies c ON ca.company_id = c.company_id
ORDER BY diff_percentage_points DESC;

