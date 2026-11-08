-- Reported-relief metrics and relief percentages by financial product in 2019.
SELECT
    p.product_name,
    COUNT(*) AS total_complaints,
    COUNT(CASE WHEN f.reported_relief IN (0, 1) THEN 1 END) AS eligible_complaints,
    COUNT(CASE WHEN f.reported_relief = 1 THEN 1 END) AS relief_complaints,
    COUNT(CASE WHEN f.reported_relief = 0 THEN 1 END) AS explanation_complaints,
    COUNT(CASE WHEN f.reported_relief IS NULL THEN 1 END) AS unlabeled_complaints,
    ROUND(100.0 * COUNT(CASE WHEN f.reported_relief = 1 THEN 1 END) / NULLIF(COUNT(CASE WHEN f.reported_relief IN (0, 1) THEN 1 END), 0), 2) AS relief_percentage
FROM fact_complaints f
JOIN dim_products p ON f.product_id = p.product_id
WHERE f.date_received >= '2019-01-01'
  AND f.date_received < '2020-01-01'
GROUP BY p.product_name
ORDER BY total_complaints DESC;

