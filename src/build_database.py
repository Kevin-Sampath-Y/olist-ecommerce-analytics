"""
Load the raw Olist CSV files into a SQLite database, then create the
analytical views.

    python -m src.build_database            # uses data/raw/*.csv
"""
from __future__ import annotations

import sqlite3
import sys

import pandas as pd

from src.config import CSV_FILES, DATE_COLUMNS, DB_PATH, RAW_DIR, SQL_DIR


def _missing_files() -> list[str]:
    return [f for f in CSV_FILES.values() if not (RAW_DIR / f).exists()]


def _normalise_dates(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Parse timestamps and store as ISO text so SQLite can sort/compare them."""
    for col in columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def build(verbose: bool = True) -> dict[str, int]:
    missing = _missing_files()
    if missing:
        sys.exit(
            "Missing raw files in data/raw/:\n  - " + "\n  - ".join(missing) +
            "\n\nDownload the Olist dataset from Kaggle (see README -> 'Using the real data')\n"
            "or generate demo data with:  python src/generate_synthetic_data.py"
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript((SQL_DIR / "01_schema.sql").read_text())

        counts: dict[str, int] = {}
        for table, filename in CSV_FILES.items():
            df = pd.read_csv(RAW_DIR / filename)
            df = _normalise_dates(df, DATE_COLUMNS.get(table, []))
            df.to_sql(table, con, if_exists="append", index=False, chunksize=20_000)
            counts[table] = len(df)
            if verbose:
                print(f"  loaded {table:<22} {len(df):>9,} rows")

        con.executescript((SQL_DIR / "02_views.sql").read_text())
        con.commit()
    finally:
        con.close()

    if verbose:
        print(f"Database ready: {DB_PATH}")
    return counts


if __name__ == "__main__":
    build()
