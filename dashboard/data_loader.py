"""
dashboard/data_loader.py — Cached data loading and transformation for Streamlit.

Loads:
  - Financials (810 rows)
  - Ratios (540 rows)
  - Market Data (46 rows)
  - Anomalies & Red-Flags (216 rows)

Provides cross-correlation caching and lookup helpers for peer comparisons.
"""

import sqlite3
from typing import Optional, Any
import pandas as pd
import streamlit as st

from config import SQLITE_PATH, COMPANIES
from anomaly.detector import audit_phase3_cross_correlation


@st.cache_data(show_spinner=False)
def load_financials() -> pd.DataFrame:
    """Load normalized financial statement facts from SQLite."""
    with sqlite3.connect(SQLITE_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM financials ORDER BY ticker, cal_year, line_item",
            conn,
        )
    return df


@st.cache_data(show_spinner=False)
def load_ratios() -> pd.DataFrame:
    """Load calculated financial ratios from SQLite."""
    with sqlite3.connect(SQLITE_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM ratios ORDER BY ticker, cal_year, ratio_category, ratio_name",
            conn,
        )
    return df


@st.cache_data(show_spinner=False)
def load_market_data() -> pd.DataFrame:
    """Load historical market data from SQLite."""
    with sqlite3.connect(SQLITE_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM market_data ORDER BY ticker, cal_year",
            conn,
        )
    return df


@st.cache_data(show_spinner=False)
def load_anomalies() -> pd.DataFrame:
    """Load calculated anomaly and red-flag scores from SQLite."""
    with sqlite3.connect(SQLITE_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM anomalies ORDER BY ticker, cal_year, anomaly_name",
            conn,
        )
    return df


@st.cache_data(show_spinner=False)
def load_cross_correlation() -> pd.DataFrame:
    """Load pre-computed cross-correlation between Phase 3 outliers and Phase 4 anomaly scores."""
    anomalies_df = load_anomalies()
    ratios_df = load_ratios()
    return audit_phase3_cross_correlation(anomalies_df, ratios_df)


def get_company_name(ticker: str) -> str:
    """Return friendly company name for a ticker."""
    return COMPANIES.get(ticker, {}).get("name", ticker)


def get_peer_ratio_timeseries(
    ratios_df: pd.DataFrame,
    tickers: list[str],
    ratio_name: str,
) -> pd.DataFrame:
    """Filter ratios table for selected peers and single ratio."""
    filtered = ratios_df[
        (ratios_df["ticker"].isin(tickers)) &
        (ratios_df["ratio_name"] == ratio_name)
    ].copy()
    return filtered.sort_values(["ticker", "cal_year"]).reset_index(drop=True)


def get_peer_anomaly_timeseries(
    anomalies_df: pd.DataFrame,
    tickers: list[str],
    anomaly_name: str,
) -> pd.DataFrame:
    """Filter anomalies table for selected peers and single anomaly model."""
    filtered = anomalies_df[
        (anomalies_df["ticker"].isin(tickers)) &
        (anomalies_df["anomaly_name"] == anomaly_name)
    ].copy()
    return filtered.sort_values(["ticker", "cal_year"]).reset_index(drop=True)
