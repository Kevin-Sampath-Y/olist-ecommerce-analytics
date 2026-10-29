-- =============================================================================
-- 01_schema.sql
-- Relational schema for the Olist Brazilian E-Commerce dataset (SQLite dialect).
--
-- Entity-relationship summary
--   customers ──< orders >── order_items >── products >── category_translation
--                   │              └──────── sellers
--                   ├──< order_payments
--                   └──< order_reviews
--   geolocation is joined on zip-code prefix (customers / sellers).
--
-- NOTE: customer_id is generated PER ORDER in Olist. The real person is
--       customer_unique_id. Using customer_id for "customer" metrics is the
--       classic mistake with this dataset - every analysis here uses
--       customer_unique_id.
-- Timestamps are stored as ISO-8601 text ('YYYY-MM-DD HH:MM:SS'), which sorts
-- and compares correctly as plain text in SQLite.
-- =============================================================================

PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS geolocation;
DROP TABLE IF EXISTS category_translation;

CREATE TABLE customers (
    customer_id               TEXT PRIMARY KEY,
    customer_unique_id        TEXT NOT NULL,
    customer_zip_code_prefix  INTEGER,
    customer_city             TEXT,
    customer_state            TEXT
);

CREATE TABLE orders (
    order_id                       TEXT PRIMARY KEY,
    customer_id                    TEXT NOT NULL REFERENCES customers(customer_id),
    order_status                   TEXT NOT NULL,
    order_purchase_timestamp       TEXT NOT NULL,
    order_approved_at              TEXT,
    order_delivered_carrier_date   TEXT,
    order_delivered_customer_date  TEXT,
    order_estimated_delivery_date  TEXT
);

CREATE TABLE products (
    product_id                   TEXT PRIMARY KEY,
    product_category_name        TEXT,
    product_name_lenght          INTEGER,   -- (sic) the source column is misspelled
    product_description_lenght   INTEGER,   -- (sic)
    product_photos_qty           INTEGER,
    product_weight_g             INTEGER,
    product_length_cm            INTEGER,
    product_height_cm            INTEGER,
    product_width_cm             INTEGER
);

CREATE TABLE sellers (
    seller_id                TEXT PRIMARY KEY,
    seller_zip_code_prefix   INTEGER,
    seller_city              TEXT,
    seller_state             TEXT
);

CREATE TABLE order_items (
    order_id             TEXT NOT NULL REFERENCES orders(order_id),
    order_item_id        INTEGER NOT NULL,
    product_id           TEXT REFERENCES products(product_id),
    seller_id            TEXT REFERENCES sellers(seller_id),
    shipping_limit_date  TEXT,
    price                REAL NOT NULL,
    freight_value        REAL NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE order_payments (
    order_id               TEXT NOT NULL REFERENCES orders(order_id),
    payment_sequential     INTEGER NOT NULL,
    payment_type           TEXT,
    payment_installments   INTEGER,
    payment_value          REAL,
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE order_reviews (
    review_id                 TEXT,
    order_id                  TEXT NOT NULL REFERENCES orders(order_id),
    review_score              INTEGER CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title      TEXT,
    review_comment_message    TEXT,
    review_creation_date      TEXT,
    review_answer_timestamp   TEXT
);

CREATE TABLE geolocation (
    geolocation_zip_code_prefix  INTEGER,
    geolocation_lat              REAL,
    geolocation_lng              REAL,
    geolocation_city             TEXT,
    geolocation_state            TEXT
);

CREATE TABLE category_translation (
    product_category_name          TEXT PRIMARY KEY,
    product_category_name_english  TEXT
);

-- Indexes on the join / filter columns used by the analysis queries
CREATE INDEX idx_customers_unique   ON customers(customer_unique_id);
CREATE INDEX idx_orders_customer    ON orders(customer_id);
CREATE INDEX idx_orders_status_date ON orders(order_status, order_purchase_timestamp);
CREATE INDEX idx_items_product      ON order_items(product_id);
CREATE INDEX idx_items_seller       ON order_items(seller_id);
CREATE INDEX idx_reviews_order      ON order_reviews(order_id);
CREATE INDEX idx_payments_order     ON order_payments(order_id);
