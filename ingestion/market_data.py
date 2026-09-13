"""
ingestion/market_data.py — Ingest and normalize historical market data via yfinance.

WHY market data matters for Phase 4:
  The Altman Z-Score requires the Market Value of Equity / Total Liabilities
  ratio (MVE/TL). While financial statement data comes from SEC EDGAR,
  market capitalization requires daily equity prices and shares outstanding
  as of each fiscal year-end date.

HANDLING IPO TIMING GRACEFULLY:
  Several companies in our fintech universe went public during 2020–2022:
    - AFRM: IPO January 2021 (FY2020 ended June 2020 is pre-IPO)
    - UPST: IPO December 2020
    - SOFI: de-SPAC June 2021
    - PGY: de-SPAC June 2022
    - SEZL: Nasdaq uplisting September 2023 (earlier ASX trading is non-US GAAP)
  For pre-IPO periods, market cap is set to NaN with flag PRE_IPO_UNAVAILABLE.
  We NEVER fabricate private valuations or assume zero.

TICKER MAPPINGS:
  - LendingClub ('LC') transitioned corporate ticker to 'HAPN' (Happen, Inc.)
    in 2026. We map 'LC' -> 'HAPN' for yfinance queries.
"""

import json
import logging
import math
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    COMPANIES,
    SQLITE_PATH,
    MARKET_DATA_RAW_DIR,
    MARKET_DATA_CSV_PATH,
)
from ingestion.store import read_financials

logger = logging.getLogger(__name__)

YFINANCE_TICKER_MAP = {
    "LC": "HAPN",  # LendingClub Corp transitioned to Happen, Inc.
}

TABLE_NAME = "market_data"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    ticker             TEXT    NOT NULL,
    cik                TEXT    NOT NULL,
    cal_year           INTEGER NOT NULL,
    fiscal_period_end  TEXT    NOT NULL,
    trading_date       TEXT,
    close_price        REAL,
    shares_outstanding REAL,
    market_cap         REAL,
    is_pre_ipo         INTEGER NOT NULL,
    data_quality       TEXT    NOT NULL,
    PRIMARY KEY (ticker, cal_year)
);
"""

UPSERT_SQL = f"""
INSERT OR REPLACE INTO {TABLE_NAME} (
    ticker, cik, cal_year, fiscal_period_end, trading_date,
    close_price, shares_outstanding, market_cap, is_pre_ipo, data_quality
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def fetch_and_normalize_market_data(use_cache: bool = True) -> pd.DataFrame:
    """Pull historical price and shares for all 9 companies and align with fiscal year-ends."""
    MARKET_DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    financials = read_financials()
    if financials.empty:
        raise ValueError("Financials table is empty — run ingestion first.")

    # Distinct periods per company: (ticker, cal_year, fiscal_period_end)
    periods = (
        financials[["ticker", "cik", "cal_year", "fiscal_period_end"]]
        .dropna(subset=["fiscal_period_end"])
        .drop_duplicates(subset=["ticker", "cal_year"])
        .sort_values(["ticker", "cal_year"])
    )

    rows: list[dict] = []

    for ticker, group in periods.groupby("ticker"):
        cik = str(group["cik"].iloc[0])
        yf_sym = YFINANCE_TICKER_MAP.get(ticker, ticker)
        raw_cache_file = MARKET_DATA_RAW_DIR / f"{ticker}.json"

        logger.info(f"[{ticker}] Fetching market data (yfinance symbol: {yf_sym})...")

        raw_data = None
        if use_cache and raw_cache_file.exists():
            try:
                with raw_cache_file.open("r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                logger.info(f"[{ticker}] Loaded cached market data from {raw_cache_file}")
            except Exception as e:
                logger.warning(f"[{ticker}] Failed to read cache, pulling fresh: {e}")

        if raw_data is None:
            t = yf.Ticker(yf_sym)
            hist = t.history(start="2019-01-01", auto_adjust=False)

            try:
                shares_s = t.get_shares_full(start="2019-01-01")
            except Exception:
                shares_s = None

            fast_shares = t.fast_info.get("shares")

            # Convert to serializable format
            hist_records = []
            if not hist.empty:
                hist_copy = hist.reset_index()
                hist_copy["DateStr"] = hist_copy["Date"].astype(str)
                hist_records = hist_copy[["DateStr", "Close", "Volume"]].to_dict("records")

            shares_records = []
            if shares_s is not None and not shares_s.empty:
                s_df = shares_s.reset_index()
                s_df.columns = ["Date", "Shares"]
                s_df["DateStr"] = s_df["Date"].astype(str)
                shares_records = s_df[["DateStr", "Shares"]].to_dict("records")

            raw_data = {
                "ticker": ticker,
                "yf_symbol": yf_sym,
                "fast_shares": fast_shares,
                "history": hist_records,
                "shares_history": shares_records,
                "fetched_at": datetime.now().isoformat(),
            }

            with raw_cache_file.open("w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2)
            logger.info(f"[{ticker}] Cached raw market data to {raw_cache_file}")

        # Parse history DataFrame
        hist_df = pd.DataFrame(raw_data.get("history", []))
        if not hist_df.empty:
            hist_df["Date"] = pd.to_datetime(hist_df["DateStr"], utc=True)
            hist_df = hist_df.sort_values("Date").reset_index(drop=True)

        shares_df = pd.DataFrame(raw_data.get("shares_history", []))
        if not shares_df.empty:
            shares_df["Date"] = pd.to_datetime(shares_df["DateStr"], utc=True)
            shares_df = shares_df.sort_values("Date").reset_index(drop=True)

        fast_shares = raw_data.get("fast_shares")

        # Match for each fiscal period end date
        for _, p_row in group.iterrows():
            cal_year = int(p_row["cal_year"])
            end_date_str = str(p_row["fiscal_period_end"])
            target_dt = pd.to_datetime(end_date_str, utc=True)

            if hist_df.empty:
                rows.append({
                    "ticker": ticker,
                    "cik": cik,
                    "cal_year": cal_year,
                    "fiscal_period_end": end_date_str,
                    "trading_date": None,
                    "close_price": float("nan"),
                    "shares_outstanding": float("nan"),
                    "market_cap": float("nan"),
                    "is_pre_ipo": 1,
                    "data_quality": "PRE_IPO_UNAVAILABLE",
                })
                continue

            earliest_trade_dt = hist_df["Date"].iloc[0]

            # If target period end is prior to the first trading day (allowing 7 days buffer for IPO weeks)
            if target_dt < earliest_trade_dt - pd.Timedelta(days=7):
                logger.info(f"[{ticker}] Year {cal_year} ({end_date_str}) is PRE-IPO (trading began {earliest_trade_dt.date()}).")
                rows.append({
                    "ticker": ticker,
                    "cik": cik,
                    "cal_year": cal_year,
                    "fiscal_period_end": end_date_str,
                    "trading_date": None,
                    "close_price": float("nan"),
                    "shares_outstanding": float("nan"),
                    "market_cap": float("nan"),
                    "is_pre_ipo": 1,
                    "data_quality": "PRE_IPO_UNAVAILABLE",
                })
                continue

            # Find last trading day on or before target_dt
            valid_trades = hist_df[hist_df["Date"] <= target_dt]
            if valid_trades.empty:
                # If within 7 days of IPO, take first available trade
                valid_trades = hist_df.head(1)

            last_trade = valid_trades.iloc[-1]
            close_price = float(last_trade["Close"])
            trading_date = last_trade["Date"].date().isoformat()

            # Find shares outstanding as of period end
            shares = None
            if not shares_df.empty:
                valid_shares = shares_df[shares_df["Date"] <= target_dt + pd.Timedelta(days=60)]
                if not valid_shares.empty:
                    shares = float(valid_shares["Shares"].iloc[-1])
                else:
                    shares = float(shares_df["Shares"].iloc[0])

            if (shares is None or math.isnan(shares) or shares <= 0) and fast_shares:
                shares = float(fast_shares)

            market_cap = close_price * shares if (shares and not math.isnan(shares)) else float("nan")

            rows.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": cal_year,
                "fiscal_period_end": end_date_str,
                "trading_date": trading_date,
                "close_price": close_price,
                "shares_outstanding": shares,
                "market_cap": market_cap,
                "is_pre_ipo": 0,
                "data_quality": "OK" if not math.isnan(market_cap) else "INCOMPLETE_SHARES",
            })

    result_df = pd.DataFrame(rows)
    return result_df.sort_values(["ticker", "cal_year"]).reset_index(drop=True)


def persist_market_data(df: pd.DataFrame) -> None:
    """Save normalized market data to SQLite and CSV."""
    if df.empty:
        return

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)

    records = [
        (
            r["ticker"], r["cik"], int(r["cal_year"]), r["fiscal_period_end"],
            r["trading_date"],
            float(r["close_price"]) if not pd.isna(r["close_price"]) else None,
            float(r["shares_outstanding"]) if not pd.isna(r["shares_outstanding"]) else None,
            float(r["market_cap"]) if not pd.isna(r["market_cap"]) else None,
            int(r["is_pre_ipo"]),
            r["data_quality"],
        )
        for _, r in df.iterrows()
    ]

    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(CREATE_TABLE_SQL)
        conn.executemany(UPSERT_SQL, records)
        conn.commit()

    logger.info(f"SQLite: upserted {len(records)} rows into {SQLITE_PATH} table '{TABLE_NAME}'")

    df.to_csv(MARKET_DATA_CSV_PATH, index=False, encoding="utf-8")
    logger.info(f"CSV: wrote {len(df)} rows to {MARKET_DATA_CSV_PATH}")


def read_market_data() -> pd.DataFrame:
    """Read normalized market data from SQLite table."""
    with sqlite3.connect(SQLITE_PATH) as conn:
        df = pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} ORDER BY ticker, cal_year",
            conn,
        )
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    df = fetch_and_normalize_market_data(use_cache=True)
    persist_market_data(df)
    print("\nMarket Data Sample:")
    print(df.head(15).to_string(index=False))
