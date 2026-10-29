"""
Execute every named query block in sql/03_*.sql ... sql/05_*.sql and save the
results as CSV files in data/processed/ (prefix 'sql_').

A block starts with a line  `-- name: <identifier>`.
  * blocks beginning with CREATE are executed as DDL (e.g. views)
  * all other blocks are run as queries and exported to sql_<identifier>.csv
"""
from __future__ import annotations

import re
import sqlite3

import pandas as pd

from src.config import DB_PATH, PROCESSED_DIR, SQL_DIR

QUERY_FILES = ["03_business_kpis.sql", "04_customer_analytics.sql", "05_delivery_and_sellers.sql"]
_NAME_RE = re.compile(r"^--\s*name:\s*(\w+)\s*$", re.MULTILINE)


def parse_blocks(text: str) -> list[tuple[str, str]]:
    """Split a SQL file into (name, statement) pairs."""
    matches = list(_NAME_RE.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        statement = text[m.end():end].strip().rstrip(";").strip()
        blocks.append((m.group(1), statement))
    return blocks


def run_all(verbose: bool = True) -> dict[str, pd.DataFrame]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}
    con = sqlite3.connect(DB_PATH)
    try:
        for filename in QUERY_FILES:
            for name, statement in parse_blocks((SQL_DIR / filename).read_text()):
                # strip leading comment lines to detect statement type
                body = "\n".join(l for l in statement.splitlines() if not l.strip().startswith("--")).strip()
                if body.upper().startswith("CREATE"):
                    con.execute(f"DROP VIEW IF EXISTS {name}")
                    con.execute(body)
                    if verbose:
                        print(f"  created view  {name}")
                    continue
                df = pd.read_sql_query(body, con)
                df.to_csv(PROCESSED_DIR / f"sql_{name}.csv", index=False)
                results[name] = df
                if verbose:
                    print(f"  query {name:<22} -> {len(df):>6,} rows")
        con.commit()
    finally:
        con.close()
    return results


if __name__ == "__main__":
    run_all()
