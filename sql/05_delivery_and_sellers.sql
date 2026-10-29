-- =============================================================================
-- 05_delivery_and_sellers.sql
-- Logistics performance, the link between delivery delays and customer
-- satisfaction, and a seller health scorecard.
-- =============================================================================

-- name: delay_vs_review
-- Does arriving late hurt review scores? Bucket orders by delay vs. the promise.
WITH d AS (
    SELECT
        *,
        CASE
            WHEN delay_days <= 0  THEN '0. On time / early'
            WHEN delay_days <= 3  THEN '1. 1-3 days late'
            WHEN delay_days <= 7  THEN '2. 4-7 days late'
            WHEN delay_days <= 14 THEN '3. 8-14 days late'
            ELSE                       '4. 15+ days late'
        END AS delay_bucket
    FROM v_orders_enriched
    WHERE order_status = 'delivered' AND review_score IS NOT NULL
)
SELECT
    delay_bucket,
    COUNT(*)                                                                 AS orders,
    ROUND(AVG(review_score), 2)                                              AS avg_review,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 1)   AS pct_1_2_star,
    ROUND(100.0 * AVG(CASE WHEN review_score = 5  THEN 1.0 ELSE 0 END), 1)   AS pct_5_star
FROM d
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- name: review_distribution
-- Review-score histogram split by on-time vs late delivery.
SELECT
    review_score,
    SUM(CASE WHEN is_late = 0 THEN 1 ELSE 0 END) AS on_time_orders,
    SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) AS late_orders
FROM v_orders_enriched
WHERE order_status = 'delivered' AND review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- name: delivery_by_month
-- Is service quality getting worse in peak months (e.g. Black Friday)?
SELECT
    purchase_month,
    COUNT(*)                         AS delivered_orders,
    ROUND(AVG(delivery_days), 1)     AS avg_delivery_days,
    ROUND(100.0 * AVG(is_late), 1)   AS late_pct,
    ROUND(AVG(review_score), 2)      AS avg_review
FROM v_orders_enriched
WHERE order_status = 'delivered' AND purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY purchase_month
ORDER BY purchase_month;

-- name: seller_scorecard
-- Seller health: revenue, satisfaction and punctuality, with a traffic-light flag.
-- Sellers with fewer than 30 delivered orders are excluded (too noisy to judge).
WITH seller_orders AS (
    SELECT seller_id, order_id, SUM(price) AS rev
    FROM order_items
    GROUP BY seller_id, order_id
),
s AS (
    SELECT
        so.seller_id,
        sl.seller_state,
        COUNT(*)                          AS orders,
        ROUND(SUM(so.rev), 2)             AS revenue,
        ROUND(AVG(o.review_score), 2)     AS avg_review,
        ROUND(100.0 * AVG(o.is_late), 1)  AS late_pct
    FROM seller_orders so
    JOIN v_orders_enriched o ON o.order_id = so.order_id
    JOIN sellers sl          ON sl.seller_id = so.seller_id
    WHERE o.order_status = 'delivered'
    GROUP BY so.seller_id, sl.seller_state
    HAVING COUNT(*) >= 30
)
SELECT
    *,
    RANK()   OVER (ORDER BY revenue DESC)    AS revenue_rank,
    NTILE(4) OVER (ORDER BY avg_review ASC)  AS review_quartile,   -- 1 = worst 25%
    CASE
        WHEN avg_review < 3.8 AND late_pct > 12 THEN 'Action: low reviews + late'
        WHEN avg_review < 3.8                   THEN 'Watch: low reviews'
        WHEN late_pct > 12                      THEN 'Watch: late deliveries'
        ELSE 'Healthy'
    END                                      AS health_flag
FROM s
ORDER BY revenue DESC;
