"""
anomaly/store.py — Persist calculated anomaly and red-flag scores to SQLite and CSV.

WHY SQLite + CSV (both):
  - SQLite: enables fast queries and relational joins across financials, ratios,
    market data, and anomalies for Phase 5 dashboard and memo generation.
  - CSV: provides lightweight, human-readable inspection for auditing.

Primary Key:
  (ticker, cal_year, anomaly_name)
  Re-running upserts updates existing records cleanly without duplicating rows.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from config import SQLITE_PATH, ANOMALIES_CSV_PATH

logger = logging.getLogger(__name__)

TABLE_NAME = "anomalies"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    ticker            TEXT    NOT NULL,
    cik               TEXT    NOT NULL,
    cal_year          INTEGER NOT NULL,
    fiscal_period_end TEXT,
    anomaly_name      TEXT    NOT NULL,
    score_value       REAL,
    score_formatted   TEXT,
    classification    TEXT    NOT NULL,
    explanation       TEXT    NOT NULL,
    PRIMARY KEY (ticker, cal_year, anomaly_name)
);
"""

UPSERT_SQL = f"""
INSERT OR REPLACE INTO {TABLE_NAME} (
    ticker, cik, cal_year, fiscal_period_end,
    anomaly_name, score_value, score_formatted,
    classification, explanation
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def write_anomalies_to_sqlite(df: pd.DataFrame, db_path: Path = SQLITE_PATH) -> None:
    """Upsert anomaly records into SQLite."""
    if df.empty:
        logger.warning("Empty DataFrame passed to write_anomalies_to_sqlite — nothing to write.")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)

    required_cols = [
        "ticker", "cik", "cal_year", "fiscal_period_end",
        "anomaly_name", "score_value", "score_formatted",
        "classification", "explanation",
    ]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required anomaly columns: {missing}")

    records = df[required_cols].values.tolist()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(CREATE_TABLE_SQL)
        conn.executemany(UPSERT_SQL, records)
        conn.commit()

    logger.info(f"SQLite: upserted {len(records)} rows into {db_path} table '{TABLE_NAME}'")


def write_anomalies_to_csv(df: pd.DataFrame, csv_path: Path = ANOMALIES_CSV_PATH) -> None:
    """Write or merge anomaly records into CSV."""
    if df.empty:
        logger.warning("Empty DataFrame passed to write_anomalies_to_csv — nothing to write.")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    key_cols = ["ticker", "cal_year", "anomaly_name"]

    if csv_path.exists() and csv_path.stat().st_size > 0:
        existing = pd.read_csv(csv_path)
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
    else:
        combined = df.copy()

    combined = combined.sort_values(key_cols).reset_index(drop=True)
    combined.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"CSV: wrote {len(combined)} total rows to {csv_path}")


def read_anomalies(db_path: Path = SQLITE_PATH, ticker: Optional[str] = None) -> pd.DataFrame:
    """Read anomalies from SQLite table as a DataFrame."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database does not exist: {db_path}")

    query = f"SELECT * FROM {TABLE_NAME}"
    params = []
    if ticker:
        query += " WHERE ticker = ?"
        params.append(ticker)
    query += " ORDER BY ticker, cal_year, anomaly_name"

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df
