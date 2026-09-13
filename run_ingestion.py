"""
run_ingestion.py — Entry point for the data ingestion pipeline.

Usage:
    # Run for two specific companies (validation checkpoint):
    python run_ingestion.py --tickers AFRM OMF

    # Run for all 9 companies in the universe:
    python run_ingestion.py --all

    # Force a fresh API pull even if cache exists:
    python run_ingestion.py --all --no-cache

    # Print the tidy table to console after ingestion:
    python run_ingestion.py --tickers AFRM OMF --show-table

This script orchestrates: edgar_client → xbrl_normalizer → store.
It is intentionally simple — no ratio or anomaly logic here (Phase 3+).
"""

import argparse
import logging
import sys

import pandas as pd

from config import COMPANIES
from ingestion.edgar_client import fetch_company_facts
from ingestion.xbrl_normalizer import normalize_company
from ingestion.store import write_to_sqlite, write_to_csv

# ---------------------------------------------------------------------------
# Logging setup — INFO level so the caller can see progress without noise
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_ingestion")


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(tickers: list[str], use_cache: bool = True) -> pd.DataFrame:
    """Run the full ingestion pipeline for the specified tickers.

    Returns the combined tidy DataFrame for all processed companies.
    """
    all_frames: list[pd.DataFrame] = []

    for ticker in tickers:
        if ticker not in COMPANIES:
            logger.error(f"Unknown ticker '{ticker}'. Valid options: {list(COMPANIES.keys())}")
            continue

        company = COMPANIES[ticker]
        logger.info(f"{'='*60}")
        logger.info(f"Processing: {ticker} — {company['name']}")
        logger.info(f"  CIK: {company['cik']}  |  FYE month: {company['fye_month']}")

        # Step 1: Fetch raw JSON (from cache or API)
        facts = fetch_company_facts(
            ticker=ticker,
            cik=company["cik"],
            use_cache=use_cache,
        )

        # Step 2: Normalize to tidy DataFrame
        df = normalize_company(
            ticker=ticker,
            cik=company["cik"],
            facts_json=facts,
            fye_month=company["fye_month"],
        )

        if df.empty:
            logger.warning(f"[{ticker}] Normalization produced an empty DataFrame — check tag map.")
            continue

        # Step 3: Persist
        write_to_sqlite(df)
        write_to_csv(df)

        all_frames.append(df)
        logger.info(f"[{ticker}] Done. {len(df)} rows stored.")

    if not all_frames:
        logger.error("No data was produced. Check ticker names and API connectivity.")
        return pd.DataFrame()

    return pd.concat(all_frames, ignore_index=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Equity Research Desk — Data Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="One or more tickers to process (e.g. AFRM OMF).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Process all 9 companies in the universe.",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cached raw JSON and always pull fresh from EDGAR.",
    )
    parser.add_argument(
        "--show-table",
        action="store_true",
        help="Print the resulting tidy table to stdout after ingestion.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    tickers = list(COMPANIES.keys()) if args.all else args.tickers
    use_cache = not args.no_cache

    logger.info(f"Starting ingestion for: {tickers}")
    logger.info(f"Cache mode: {'ON (skipping API for cached files)' if use_cache else 'OFF (fresh pull)'}")

    combined = run_pipeline(tickers=tickers, use_cache=use_cache)

    if not combined.empty:
        logger.info(f"\n{'='*60}")
        logger.info(f"Ingestion complete. Total rows: {len(combined)}")
        logger.info(f"Companies: {combined['ticker'].unique().tolist()}")
        logger.info(f"Calendar years: {sorted(combined['cal_year'].unique().tolist())}")
        logger.info(f"Data quality summary:")

        # Print detailed quality summary
        dq_summary = (
            combined.groupby(["ticker", "data_quality"])
            .size()
            .rename("count")
            .reset_index()
        )
        print("\n" + "="*60)
        print("DETAILED DATA QUALITY BREAKDOWN")
        print("="*60)
        print(dq_summary.to_string(index=False))

        # Print cross-company flag matrix
        print("\n" + "="*60)
        print("DATA QUALITY MATRIX (BY TICKER)")
        print("="*60)
        matrix_df = combined.copy()
        matrix_df["flag_category"] = matrix_df["data_quality"].apply(
            lambda x: "FALLBACK" if x.startswith("FALLBACK_") else (
                "ZERO_VALUE" if "ZERO_VALUE" in x else x
            )
        )
        piv = matrix_df.pivot_table(
            index="ticker",
            columns="flag_category",
            values="cal_year",
            aggfunc="count",
            fill_value=0
        )
        piv["TOTAL"] = piv.sum(axis=1)
        print(piv.to_string())

        if args.show_table:
            pd.set_option("display.max_rows", 200)
            pd.set_option("display.max_columns", 20)
            pd.set_option("display.width", 140)
            pd.set_option("display.float_format", "{:,.0f}".format)
            print("\n" + "="*60)
            print("TIDY TABLE OUTPUT")
            print("="*60)
            display_cols = ["ticker", "cal_year", "fiscal_period_end",
                            "line_item", "value", "source_tag", "data_quality"]
            print(combined[display_cols].to_string(index=False))
    else:
        sys.exit(1)
