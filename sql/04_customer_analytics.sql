-- =============================================================================
-- 04_customer_analytics.sql
-- Customer segmentation (RFM), cohort retention and repeat-purchase timing.
--
-- KEY DATA INSIGHT: ~97% of Olist customers buy exactly once, so "Frequency"
-- has almost no variance. Classic RFM with quintiles on all three dimensions
-- would put nearly everyone in the same F bucket. We therefore score:
--     R -> quintile (NTILE 5) of recency        (5 = bought most recently)
--     F -> fixed rule: 1 order = 1, 2 orders = 3, 3+ orders = 5
--     M -> quintile (NTILE 5) of total spend
-- =============================================================================

-- name: v_customer_rfm
-- (DDL block: creates a view used by the queries below)
CREATE VIEW IF NOT EXISTS v_customer_rfm AS
WITH valid AS (
    SELECT *
    FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable') AND items_value IS NOT NULL
),
ref AS (
    SELECT date(MAX(purchased_at), '+1 day') AS ref_date FROM valid
),
base AS (
    SELECT
        customer_unique_id,
        MAX(customer_state)                                                         AS state,
        CAST(julianday((SELECT ref_date FROM ref)) - julianday(MAX(purchased_at)) AS INTEGER) AS recency_days,
        COUNT(*)                                                                    AS frequency,
        ROUND(SUM(items_value), 2)                                                  AS monetary
    FROM valid
    GROUP BY customer_unique_id
),
scored AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days DESC, customer_unique_id) AS r_score,
        CASE WHEN frequency = 1 THEN 1 WHEN frequency = 2 THEN 3 ELSE 5 END AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC, customer_unique_id)      AS m_score
    FROM base
)
SELECT
    *,
    CASE
        WHEN r_score >= 4 AND f_score >= 3 THEN 'Champions'
        WHEN f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 4 AND m_score >= 4 THEN 'New High-Spenders'
        WHEN r_score >= 4                  THEN 'Recent Customers'
        WHEN r_score <= 2 AND m_score >= 4 THEN 'At-Risk High-Value'
        WHEN r_score <= 2                  THEN 'Hibernating'
        ELSE 'Needs Attention'
    END AS segment
FROM scored;

-- name: customer_rfm
SELECT * FROM v_customer_rfm;

-- name: rfm_segment_summary
SELECT
    segment,
    COUNT(*)                                                         AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS customer_pct,
    ROUND(SUM(monetary), 2)                                          AS revenue,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1)     AS revenue_pct,
    ROUND(AVG(monetary), 2)                                          AS avg_spend,
    ROUND(AVG(recency_days), 0)                                      AS avg_recency_days
FROM v_customer_rfm
GROUP BY segment
ORDER BY revenue DESC;

-- name: cohort_retention
-- Customers grouped by month of FIRST purchase; share that purchases again in
-- month +1, +2, ... Month 0 is always 100%.
WITH valid AS (
    SELECT customer_unique_id, purchase_month
    FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
),
first_m AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort_month
    FROM valid
    GROUP BY customer_unique_id
),
activity AS (
    SELECT DISTINCT
        v.customer_unique_id,
        f.cohort_month,
        (CAST(substr(v.purchase_month, 1, 4) AS INTEGER) - CAST(substr(f.cohort_month, 1, 4) AS INTEGER)) * 12
        + CAST(substr(v.purchase_month, 6, 2) AS INTEGER) - CAST(substr(f.cohort_month, 6, 2) AS INTEGER) AS month_index
    FROM valid v
    JOIN first_m f ON f.customer_unique_id = v.customer_unique_id
),
sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size FROM first_m GROUP BY cohort_month
)
SELECT
    a.cohort_month,
    a.month_index,
    s.cohort_size,
    COUNT(*)                                       AS active_customers,
    ROUND(100.0 * COUNT(*) / s.cohort_size, 2)     AS retention_pct
FROM activity a
JOIN sizes s ON s.cohort_month = a.cohort_month
WHERE a.cohort_month BETWEEN '2017-01' AND '2018-08'
GROUP BY a.cohort_month, a.month_index, s.cohort_size
ORDER BY a.cohort_month, a.month_index;

-- name: repeat_gap
-- For customers who bought again: how long between the 1st and 2nd order?
WITH seq AS (
    SELECT
        customer_unique_id,
        purchased_at,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchased_at) AS n
    FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
),
pairs AS (
    SELECT
        a.customer_unique_id,
        julianday(b.purchased_at) - julianday(a.purchased_at) AS gap_days
    FROM seq a
    JOIN seq b ON b.customer_unique_id = a.customer_unique_id AND a.n = 1 AND b.n = 2
)
SELECT
    CASE
        WHEN gap_days < 1   THEN '0-1 day'
        WHEN gap_days < 30  THEN '1-30 days'
        WHEN gap_days < 90  THEN '31-90 days'
        WHEN gap_days < 180 THEN '91-180 days'
        ELSE '180+ days'
    END                           AS gap_bucket,
    COUNT(*)                      AS customers,
    ROUND(AVG(gap_days), 1)       AS avg_gap_days
FROM pairs
GROUP BY gap_bucket
ORDER BY MIN(gap_days);
