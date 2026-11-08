-- Monthly complaint volume and month-over-month percentage change in 2019.
WITH monthly_counts AS (
    SELECT
        strftime('%Y-%m', date_received) AS month,
        COUNT(*) AS complaint_count
    FROM fact_complaints
    WHERE date_received >= '2019-01-01'
      AND date_received < '2020-01-01'
    GROUP BY strftime('%Y-%m', date_received)
)
SELECT
    month,
    complaint_count,
    LAG(complaint_count) OVER (ORDER BY month) AS prev_month_count,
    ROUND(100.0 * (complaint_count - LAG(complaint_count) OVER (ORDER BY month)) / NULLIF(LAG(complaint_count) OVER (ORDER BY month), 0), 2) AS mom_pct_change
FROM monthly_counts
ORDER BY month ASC;

