"""
ratios/store.py — Persist calculated financial ratios to SQLite and CSV.

WHY SQLite + CSV (both):
  - SQLite: enables relational queries across financials and ratios, e.g.:
      SELECT f.ticker, f.cal_year, f.value as revenue, r.value as roe
      FROM financials f JOIN ratios r ON ...
    Allows Phase 4 anomaly detection and Phase 5 dashboard to query easily.
  - CSV: provides inspectable, lightweight storage for Streamlit and manual audit.

Compound primary key: (ticker, cal_year, ratio_name).
Re-running upserts rather than duplicating rows.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from config import SQLITE_PATH, RATIOS_CSV_PATH

logger = logging.getLogger(__name__)

TABLE_NAME = "ratios"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    ticker            TEXT    NOT NULL,
    cik               TEXT    NOT NULL,
    cal_year          INTEGER NOT NULL,
    fiscal_period_end TEXT,
    ratio_category    TEXT    NOT NULL,
    ratio_name        TEXT    NOT NULL,
    value             REAL,
    value_formatted   TEXT,
    data_quality      TEXT    NOT NULL,
    quality_note      TEXT,
    PRIMARY KEY (ticker, cal_year, ratio_name)
);
"""

UPSERT_SQL = f"""
INSERT OR REPLACE INTO {TABLE_NAME} (
    ticker, cik, cal_year, fiscal_period_end,
    ratio_category, ratio_name, value, value_formatted,
    data_quality, quality_note
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def write_ratios_to_sqlite(df: pd.DataFrame, db_path: Path = SQLITE_PATH) -> None:
    """Upsert a tidy ratios DataFrame into SQLite."""
    if df.empty:
        logger.warning("Empty DataFrame passed to write_ratios_to_sqlite — nothing to write.")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)

    required_cols = [
        "ticker", "cik", "cal_year", "fiscal_period_end",
        "ratio_category", "ratio_name", "value", "value_formatted",
        "data_quality", "quality_note",
    ]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required ratio columns: {missing}")

    records = df[required_cols].values.tolist()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(CREATE_TABLE_SQL)
        conn.executemany(UPSERT_SQL, records)
        conn.commit()

    logger.info(f"SQLite: upserted {len(records)} rows into {db_path} table '{TABLE_NAME}'")


def write_ratios_to_csv(df: pd.DataFrame, csv_path: Path = RATIOS_CSV_PATH) -> None:
    """Write or merge ratios into CSV."""
    if df.empty:
        logger.warning("Empty DataFrame passed to write_ratios_to_csv — nothing to write.")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    key_cols = ["ticker", "cal_year", "ratio_name"]

    if csv_path.exists() and csv_path.stat().st_size > 0:
        existing = pd.read_csv(csv_path)
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
    else:
        combined = df.copy()

    combined = combined.sort_values(key_cols).reset_index(drop=True)
    combined.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"CSV: wrote {len(combined)} total rows to {csv_path}")


def read_ratios(db_path: Path = SQLITE_PATH) -> pd.DataFrame:
    """Read all ratios from SQLite table as a tidy DataFrame."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database does not exist: {db_path}")

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} ORDER BY ticker, cal_year, ratio_category, ratio_name",
            conn,
        )
    return df
