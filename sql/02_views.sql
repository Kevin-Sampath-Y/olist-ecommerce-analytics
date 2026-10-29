-- =============================================================================
-- 02_views.sql
-- Reusable analytical views. Every business query downstream reads from these,
-- so metric definitions live in exactly ONE place.
--
-- METRIC DEFINITIONS
--   Revenue (GMV)  = SUM(item price), excluding freight, for orders that are
--                    not canceled / unavailable.
--   Delivery days  = delivered-to-customer date  minus  purchase date.
--   Delay days     = delivered date minus ESTIMATED delivery date
--                    (> 0 means the order arrived late vs the promise).
--   Late order     = delivered after the estimated delivery date.
-- =============================================================================

DROP VIEW IF EXISTS v_order_value;
DROP VIEW IF EXISTS v_order_review;
DROP VIEW IF EXISTS v_orders_enriched;
DROP VIEW IF EXISTS v_items_enriched;

-- One row per order: money totals computed from line items ----------------------
CREATE VIEW v_order_value AS
SELECT
    order_id,
    COUNT(*)                       AS n_items,
    ROUND(SUM(price), 2)           AS items_value,
    ROUND(SUM(freight_value), 2)   AS freight_value,
    ROUND(SUM(price + freight_value), 2) AS order_value
FROM order_items
GROUP BY order_id;

-- Some orders carry more than one review: keep only the most recent one ---------
CREATE VIEW v_order_review AS
SELECT order_id, review_score
FROM (
    SELECT
        order_id,
        review_score,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY review_answer_timestamp DESC, review_creation_date DESC
        ) AS rn
    FROM order_reviews
)
WHERE rn = 1;

-- One row per order, joined to customer, money and review ----------------------
CREATE VIEW v_orders_enriched AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,
    o.order_status,
    o.order_purchase_timestamp                         AS purchased_at,
    substr(o.order_purchase_timestamp, 1, 7)           AS purchase_month,   -- 'YYYY-MM'
    date(o.order_purchase_timestamp)                   AS purchase_date,
    o.order_delivered_customer_date                    AS delivered_at,
    o.order_estimated_delivery_date                    AS estimated_at,
    v.n_items,
    v.items_value,
    v.freight_value,
    v.order_value,
    CASE WHEN o.order_delivered_customer_date IS NOT NULL
         THEN julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)
    END                                                AS delivery_days,
    CASE WHEN o.order_delivered_customer_date IS NOT NULL
         THEN julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)
    END                                                AS delay_days,
    CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
         THEN 1 ELSE 0 END                             AS is_late,
    r.review_score
FROM orders o
JOIN customers c           ON c.customer_id = o.customer_id
LEFT JOIN v_order_value v  ON v.order_id    = o.order_id
LEFT JOIN v_order_review r ON r.order_id    = o.order_id;

-- One row per order line, with English category and seller location -------------
CREATE VIEW v_items_enriched AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.price,
    i.freight_value,
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
    s.seller_state,
    o.order_status,
    substr(o.order_purchase_timestamp, 1, 7)  AS purchase_month
FROM order_items i
JOIN orders o                        ON o.order_id = i.order_id
LEFT JOIN products p                 ON p.product_id = i.product_id
LEFT JOIN category_translation t     ON t.product_category_name = p.product_category_name
LEFT JOIN sellers s                  ON s.seller_id = i.seller_id;
