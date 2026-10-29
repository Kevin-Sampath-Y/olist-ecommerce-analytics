"""Export tidy tables for Power BI / Tableau into data/processed/bi/."""
from __future__ import annotations

import sqlite3

import pandas as pd

from src.config import DB_PATH, PROCESSED_DIR

TABLES = {
    "fact_orders": "SELECT * FROM v_orders_enriched",
    "fact_order_items": "SELECT * FROM v_items_enriched",
    "dim_customer_rfm": "SELECT * FROM v_customer_rfm",
    "dim_seller_scorecard": None,  # produced by run_sql, copied below
}


def export(verbose: bool = True) -> None:
    out = PROCESSED_DIR / "bi"
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        for name, query in TABLES.items():
            if query is None:
                continue
            df = pd.read_sql_query(query, con)
            df.to_csv(out / f"{name}.csv", index=False)
            if verbose:
                print(f"  bi/{name}.csv  ({len(df):,} rows)")
    finally:
        con.close()
    for src, dst in [("sql_seller_scorecard.csv", "dim_seller_scorecard.csv"),
                     ("sql_category_pareto.csv", "agg_category_pareto.csv"),
                     ("sql_state_performance.csv", "agg_state_performance.csv"),
                     ("sql_cohort_retention.csv", "agg_cohort_retention.csv")]:
        pd.read_csv(PROCESSED_DIR / src).to_csv(out / dst, index=False)
