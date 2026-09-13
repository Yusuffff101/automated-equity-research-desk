"""
ingestion/store.py — Persist the normalized tidy DataFrame to SQLite and CSV.

WHY SQLite + CSV (both):
  - SQLite: allows the ratio engine and anomaly module to run SQL queries
    directly (e.g. "give me all revenue rows across all companies for 2023")
    without loading everything into memory. Re-runnable pipelines can upsert
    new data without duplicating rows.
  - CSV: lets the Streamlit dashboard read data with a simple pd.read_csv()
    call without requiring SQLite on the deployment host, and makes the
    output human-inspectable without any tooling.

The SQLite table schema uses a compound primary key of
(ticker, cal_year, line_item) so that re-running the pipeline for a
subset of companies upserts rather than appends duplicate rows.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from config import SQLITE_PATH, CSV_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

TABLE_NAME = "financials"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    ticker            TEXT    NOT NULL,
    cik               TEXT    NOT NULL,
    cal_year          INTEGER NOT NULL,
    fiscal_period_end TEXT,
    line_item         TEXT    NOT NULL,
    value             REAL,
    source_tag        TEXT,
    data_quality      TEXT    NOT NULL,
    form              TEXT,
    filed             TEXT,
    PRIMARY KEY (ticker, cal_year, line_item)
);
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_to_sqlite(df: pd.DataFrame, db_path: Path = SQLITE_PATH) -> None:
    """Upsert a normalized tidy DataFrame into the SQLite financials table.

    Uses INSERT OR REPLACE semantics so that re-running the pipeline for
    any company overwrites existing rows for that (ticker, cal_year, line_item)
    combination, rather than creating duplicates.

    Args:
        df:      The tidy DataFrame produced by xbrl_normalizer.normalize_company().
        db_path: Path to the SQLite database file (created if absent).
    """
    if df.empty:
        logger.warning("write_to_sqlite called with empty DataFrame — nothing written.")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    try:
        conn.execute(CREATE_TABLE_SQL)

        # We use INSERT OR REPLACE rather than df.to_sql() to honour the
        # compound primary key and avoid duplicates on re-runs.
        cols = [
            "ticker", "cik", "cal_year", "fiscal_period_end",
            "line_item", "value", "source_tag", "data_quality",
            "form", "filed",
        ]
        placeholders = ", ".join(["?"] * len(cols))
        col_names    = ", ".join(cols)

        # Ensure the DataFrame has all expected columns (fill missing with None)
        for col in cols:
            if col not in df.columns:
                df[col] = None

        records = df[cols].where(pd.notna(df[cols]), None).values.tolist()

        conn.executemany(
            f"INSERT OR REPLACE INTO {TABLE_NAME} ({col_names}) VALUES ({placeholders})",
            records,
        )
        conn.commit()
        logger.info(f"SQLite: upserted {len(records)} rows into {db_path}")

    finally:
        conn.close()


def write_to_csv(df: pd.DataFrame, csv_path: Path = CSV_PATH) -> None:
    """Write (or append) the tidy DataFrame to a CSV file.

    On first run, creates the CSV with a header.
    On subsequent runs for additional companies, appends rows without
    rewriting the header — then deduplicates by (ticker, cal_year, line_item)
    in place so the CSV stays consistent with SQLite.

    Args:
        df:       The tidy DataFrame.
        csv_path: Path to the CSV file.
    """
    if df.empty:
        logger.warning("write_to_csv called with empty DataFrame — nothing written.")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.exists():
        # Read existing CSV, merge, deduplicate (latest data wins)
        existing = pd.read_csv(csv_path, dtype=str)
        combined = pd.concat([existing, df.astype(str)], ignore_index=True)
        combined = (
            combined
            .sort_values("filed", ascending=False, na_position="last")
            .drop_duplicates(subset=["ticker", "cal_year", "line_item"], keep="first")
            .sort_values(["ticker", "cal_year", "line_item"])
            .reset_index(drop=True)
        )
        combined.to_csv(csv_path, index=False)
        logger.info(f"CSV: merged & wrote {len(combined)} total rows to {csv_path}")
    else:
        df.to_csv(csv_path, index=False)
        logger.info(f"CSV: wrote {len(df)} rows to {csv_path}")


def read_financials(db_path: Path = SQLITE_PATH) -> pd.DataFrame:
    """Convenience function: read the full financials table from SQLite.

    Used by the ratio engine and anomaly module in later phases.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"Financials database not found at {db_path}. "
            "Run the ingestion pipeline first: python run_ingestion.py --all"
        )
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()
    return df
