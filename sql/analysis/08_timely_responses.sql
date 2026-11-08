-- Operational timely-response compliance metrics by financial product in 2019.
SELECT
    p.product_name,
    COUNT(*) AS total_complaints,
    COUNT(CASE WHEN f.timely_response = 'Yes' THEN 1 END) AS timely_count,
    COUNT(CASE WHEN f.timely_response = 'No' THEN 1 END) AS untimely_count,
    COUNT(CASE WHEN f.timely_response NOT IN ('Yes', 'No') OR f.timely_response IS NULL THEN 1 END) AS unexpected_or_missing_count,
    ROUND(100.0 * COUNT(CASE WHEN f.timely_response = 'Yes' THEN 1 END) / NULLIF(COUNT(*), 0), 2) AS timely_percentage
FROM fact_complaints f
JOIN dim_products p ON f.product_id = p.product_id
WHERE f.date_received >= '2019-01-01'
  AND f.date_received < '2020-01-01'
GROUP BY p.product_name
ORDER BY total_complaints DESC;

