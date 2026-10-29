"""
Automated checks for the SQL layer. They build a small synthetic database in a
temporary folder, so they run in seconds and never touch your real data.

    pytest -q
"""
import sqlite3

import pandas as pd
import pytest

from src.build_database import _normalise_dates
from src.config import CSV_FILES, DATE_COLUMNS, SQL_DIR
from src.generate_synthetic_data import generate
from src.run_sql import QUERY_FILES, parse_blocks

SYNTH_TO_TABLE = {csv_name.removesuffix(".csv"): table for table, csv_name in CSV_FILES.items()}


@pytest.fixture(scope="module")
def con():
    tables = generate(n_orders=3000, seed=7)
    c = sqlite3.connect(":memory:")
    c.executescript((SQL_DIR / "01_schema.sql").read_text())
    for name, df in tables.items():
        table = SYNTH_TO_TABLE[name]
        df = _normalise_dates(df.copy(), DATE_COLUMNS.get(table, []))
        df.to_sql(table, c, if_exists="append", index=False)
    c.executescript((SQL_DIR / "02_views.sql").read_text())
    # create the RFM view defined in 04_customer_analytics.sql
    for name, stmt in parse_blocks((SQL_DIR / "04_customer_analytics.sql").read_text()):
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body.upper().startswith("CREATE"):
            c.execute(body)
    yield c
    c.close()


def q(con, sql):
    return pd.read_sql_query(sql, con)


def test_primary_keys_are_unique(con):
    assert q(con, "SELECT COUNT(*) - COUNT(DISTINCT order_id) AS d FROM orders")["d"][0] == 0


def test_every_order_has_exactly_one_row_in_enriched_view(con):
    n_orders = q(con, "SELECT COUNT(*) AS n FROM orders")["n"][0]
    n_view = q(con, "SELECT COUNT(*) AS n FROM v_orders_enriched")["n"][0]
    assert n_orders == n_view  # joins must not duplicate or drop orders


def test_review_view_keeps_one_review_per_order(con):
    d = q(con, "SELECT COUNT(*) - COUNT(DISTINCT order_id) AS d FROM v_order_review")["d"][0]
    assert d == 0


def test_revenue_matches_pandas(con):
    sql_rev = q(con, "SELECT SUM(items_value) AS r FROM v_orders_enriched "
                     "WHERE order_status NOT IN ('canceled','unavailable')")["r"][0]
    items = q(con, "SELECT i.price FROM order_items i JOIN orders o USING(order_id) "
                   "WHERE o.order_status NOT IN ('canceled','unavailable')")
    assert sql_rev == pytest.approx(items["price"].sum(), rel=1e-9)


def test_late_flag_consistent_with_delay_days(con):
    d = q(con, "SELECT is_late, delay_days FROM v_orders_enriched WHERE delivered_at IS NOT NULL")
    assert ((d["delay_days"] > 0).astype(int) == d["is_late"]).all()


def test_customer_metrics_use_unique_id(con):
    # customer_id is per-order, so distinct customer_id >= distinct customer_unique_id
    d = q(con, "SELECT COUNT(DISTINCT customer_id) a, COUNT(DISTINCT customer_unique_id) b FROM customers")
    assert d["a"][0] > d["b"][0]


def test_rfm_scores_are_in_range_and_segments_complete(con):
    r = q(con, "SELECT * FROM v_customer_rfm")
    assert r["r_score"].between(1, 5).all() and r["m_score"].between(1, 5).all()
    assert r["f_score"].isin([1, 3, 5]).all()
    assert r["segment"].notna().all()
    assert r["customer_unique_id"].is_unique


def test_rfm_covers_all_valid_customers(con):
    n_rfm = q(con, "SELECT COUNT(*) n FROM v_customer_rfm")["n"][0]
    n_valid = q(con, "SELECT COUNT(DISTINCT customer_unique_id) n FROM v_orders_enriched "
                     "WHERE order_status NOT IN ('canceled','unavailable') AND items_value IS NOT NULL")["n"][0]
    assert n_rfm == n_valid


def test_all_named_queries_execute(con):
    for fname in QUERY_FILES:
        for name, stmt in parse_blocks((SQL_DIR / fname).read_text()):
            body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
            if body.upper().startswith("CREATE"):
                continue
            df = q(con, body)
            assert isinstance(df, pd.DataFrame), name


def test_cohort_month0_is_always_100_percent(con):
    body = next(s for n, s in parse_blocks((SQL_DIR / "04_customer_analytics.sql").read_text()) if n == "cohort_retention")
    c = q(con, body)
    assert (c.loc[c["month_index"] == 0, "retention_pct"] == 100).all()


def test_parse_blocks_splits_named_queries():
    text = "-- header\n-- name: a\nSELECT 1;\n-- name: b\nSELECT 2;"
    assert [n for n, _ in parse_blocks(text)] == ["a", "b"]
