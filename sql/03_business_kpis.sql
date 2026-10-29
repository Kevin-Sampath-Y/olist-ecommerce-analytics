-- =============================================================================
-- 03_business_kpis.sql
-- Business performance queries: KPIs, revenue trend, category mix, geography,
-- payments and buying behaviour.
--
-- Each block starts with "-- name: <id>". src/run_sql.py executes every block and
-- saves SELECT results to data/processed/sql_<id>.csv (used by the dashboard
-- and by Power BI / Tableau).
-- SQL features demonstrated: CTEs, window functions (LAG, RANK, running SUM,
-- moving AVG), conditional aggregation, ROW_NUMBER, date arithmetic.
-- =============================================================================

-- name: kpi_summary
-- Headline numbers for the dashboard cards (single row).
WITH valid AS (
    SELECT * FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable') AND items_value IS NOT NULL
),
cust AS (
    SELECT customer_unique_id, COUNT(*) AS n_orders
    FROM valid
    GROUP BY customer_unique_id
),
delivered AS (
    SELECT * FROM v_orders_enriched WHERE order_status = 'delivered'
)
SELECT
    (SELECT COUNT(*) FROM orders)                                             AS total_orders,
    (SELECT COUNT(*) FROM valid)                                              AS valid_orders,
    (SELECT COUNT(*) FROM cust)                                               AS unique_customers,
    ROUND((SELECT SUM(items_value) FROM valid), 2)                            AS revenue,
    ROUND((SELECT AVG(items_value) FROM valid), 2)                            AS avg_order_value,
    ROUND((SELECT AVG(review_score) FROM valid
           WHERE review_score IS NOT NULL), 2)                                AS avg_review_score,
    ROUND(100.0 * (SELECT SUM(is_late) FROM delivered)
                / (SELECT COUNT(*) FROM delivered), 2)                        AS late_delivery_pct,
    ROUND((SELECT AVG(delivery_days) FROM delivered), 2)                      AS avg_delivery_days,
    ROUND(100.0 * (SELECT COUNT(*) FROM cust WHERE n_orders > 1)
                / (SELECT COUNT(*) FROM cust), 2)                             AS repeat_customer_pct;

-- name: monthly_revenue
-- Monthly trend with month-over-month growth and a 3-month moving average.
-- Months outside 2017-01..2018-08 are partial / near-empty in the source data.
WITH m AS (
    SELECT
        purchase_month,
        COUNT(*)                            AS orders,
        COUNT(DISTINCT customer_unique_id)  AS customers,
        ROUND(SUM(items_value), 2)          AS revenue,
        ROUND(AVG(items_value), 2)          AS aov
    FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    orders,
    customers,
    revenue,
    aov,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY purchase_month))
                / LAG(revenue) OVER (ORDER BY purchase_month), 1)             AS revenue_mom_pct,
    ROUND(AVG(revenue) OVER (ORDER BY purchase_month
                             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)    AS revenue_3m_avg
FROM m
ORDER BY purchase_month;

-- name: category_pareto
-- Pareto / ABC analysis: which categories produce 70% / 90% of revenue.
WITH cat AS (
    SELECT
        category,
        COUNT(DISTINCT order_id)   AS orders,
        COUNT(*)                   AS items,
        ROUND(SUM(price), 2)       AS revenue,
        ROUND(AVG(price), 2)       AS avg_price
    FROM v_items_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY category
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY revenue DESC)                                      AS revenue_rank,
        ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)                         AS revenue_share_pct,
        ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    / SUM(revenue) OVER (), 2)                                   AS cumulative_share_pct
    FROM cat
)
SELECT
    *,
    CASE
        WHEN cumulative_share_pct - revenue_share_pct < 70 THEN 'A'
        WHEN cumulative_share_pct - revenue_share_pct < 90 THEN 'B'
        ELSE 'C'
    END AS abc_class
FROM ranked
ORDER BY revenue_rank;

-- name: category_quality
-- Revenue vs customer satisfaction by category (one row per category-order,
-- so multi-item orders are not double counted).
WITH cat_orders AS (
    SELECT category, order_id, SUM(price) AS rev
    FROM v_items_enriched
    WHERE order_status = 'delivered'
    GROUP BY category, order_id
)
SELECT
    c.category,
    COUNT(*)                                                         AS orders,
    ROUND(SUM(c.rev), 2)                                             AS revenue,
    ROUND(AVG(o.review_score), 2)                                    AS avg_review,
    ROUND(100.0 * AVG(CASE WHEN o.review_score <= 2 THEN 1.0 ELSE 0 END), 1) AS pct_bad_reviews
FROM cat_orders c
JOIN v_orders_enriched o ON o.order_id = c.order_id
WHERE o.review_score IS NOT NULL
GROUP BY c.category
HAVING COUNT(*) >= 100
ORDER BY revenue DESC;

-- name: state_performance
-- Geographic view: revenue concentration, freight burden and service quality.
SELECT
    customer_state,
    COUNT(DISTINCT customer_unique_id)                                     AS customers,
    COUNT(*)                                                               AS orders,
    ROUND(SUM(items_value), 2)                                             AS revenue,
    ROUND(AVG(items_value), 2)                                             AS aov,
    ROUND(100.0 * SUM(freight_value) / SUM(items_value), 1)                AS freight_pct_of_revenue,
    ROUND(AVG(CASE WHEN order_status = 'delivered' THEN delivery_days END), 1)   AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN order_status = 'delivered' THEN is_late END), 1) AS late_pct,
    ROUND(AVG(review_score), 2)                                            AS avg_review
FROM v_orders_enriched
WHERE order_status NOT IN ('canceled', 'unavailable') AND items_value IS NOT NULL
GROUP BY customer_state
ORDER BY revenue DESC;

-- name: payment_mix
-- How customers pay. Installments matter in Brazil (parcelamento).
SELECT
    p.payment_type,
    COUNT(DISTINCT p.order_id)                                         AS orders,
    ROUND(SUM(p.payment_value), 2)                                     AS payment_value,
    ROUND(100.0 * SUM(p.payment_value) / SUM(SUM(p.payment_value)) OVER (), 1) AS value_share_pct,
    ROUND(AVG(p.payment_installments), 1)                              AS avg_installments
FROM order_payments p
JOIN orders o ON o.order_id = p.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY p.payment_type
ORDER BY payment_value DESC;

-- name: weekday_hour
-- When do people buy? (0 = Sunday ... 6 = Saturday; hour in 0..23)
SELECT
    CAST(strftime('%w', purchased_at) AS INTEGER) AS dow,
    CAST(strftime('%H', purchased_at) AS INTEGER) AS hour,
    COUNT(*)                                      AS orders
FROM v_orders_enriched
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY dow, hour
ORDER BY dow, hour;

-- name: new_vs_returning
-- Monthly split of orders / revenue from first-time vs repeat buyers.
WITH ranked AS (
    SELECT
        customer_unique_id,
        purchase_month,
        items_value,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchased_at) AS order_seq
    FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable') AND items_value IS NOT NULL
)
SELECT
    purchase_month,
    SUM(CASE WHEN order_seq = 1 THEN 1 ELSE 0 END)                     AS new_customer_orders,
    SUM(CASE WHEN order_seq > 1 THEN 1 ELSE 0 END)                     AS repeat_orders,
    ROUND(SUM(items_value), 2)                                         AS revenue,
    ROUND(SUM(CASE WHEN order_seq > 1 THEN items_value ELSE 0 END), 2) AS repeat_revenue,
    ROUND(100.0 * SUM(CASE WHEN order_seq > 1 THEN items_value ELSE 0 END)
                / SUM(items_value), 1)                                 AS repeat_revenue_pct
FROM ranked
WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY purchase_month
ORDER BY purchase_month;

-- name: state_monthly
-- Pre-aggregated state x month table. Powers the state filter in the HTML
-- dashboard (sums are stored so ratios can be recomputed after filtering).
SELECT
    customer_state                                                          AS state,
    purchase_month,
    COUNT(*)                                                                AS orders,
    ROUND(SUM(items_value), 2)                                              AS revenue,
    SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END)             AS delivered,
    SUM(CASE WHEN order_status = 'delivered' THEN is_late ELSE 0 END)       AS late,
    SUM(review_score)                                                       AS review_sum,
    COUNT(review_score)                                                     AS review_n,
    ROUND(SUM(CASE WHEN order_status = 'delivered' THEN delivery_days END), 1) AS delivery_days_sum
FROM v_orders_enriched
WHERE order_status NOT IN ('canceled', 'unavailable')
  AND items_value IS NOT NULL
  AND purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY customer_state, purchase_month
ORDER BY customer_state, purchase_month;
