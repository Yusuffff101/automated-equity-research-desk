"""
run_ratios.py — CLI entry point for the Financial Ratio Engine.

Usage:
    # Compute and persist ratios for all 9 companies:
    python run_ratios.py --all

    # Compute for specific companies:
    python run_ratios.py --tickers AFRM OMF

    # Show full ratio table in terminal:
    python run_ratios.py --all --show-table
"""

import argparse
import logging
import math
import sys

import pandas as pd

from config import COMPANIES
from ingestion.store import read_financials
from ratios.ratio_engine import compute_all_ratios
from ratios.store import write_ratios_to_sqlite, write_ratios_to_csv, read_ratios

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_ratios")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Equity Research Desk — Financial Ratio Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Compute ratios for all 9 companies in the universe.",
    )
    group.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="One or more tickers to process (e.g. AFRM OMF).",
    )
    parser.add_argument(
        "--show-table",
        action="store_true",
        help="Print the full ratio table to stdout.",
    )
    return parser.parse_args()


def display_validation_checkpoint(ratios_df: pd.DataFrame, financials_df: pd.DataFrame) -> None:
    """Print the required validation checkpoint sections."""
    print("\n" + "=" * 78)
    print("PHASE 3 VALIDATION CHECKPOINT: FINANCIAL RATIO ENGINE")
    print("=" * 78)

    # 1. Step 0 total_debt Fix Verification
    print("\n" + "-" * 78)
    print("1. STEP 0 VERIFICATION: TOTAL DEBT COVERAGE")
    print("-" * 78)
    debt_sub = financials_df[financials_df["line_item"] == "total_debt"]
    debt_summary = (
        debt_sub.groupby("ticker")
        .apply(
            lambda g: pd.Series({
                "Total Rows": len(g),
                "Populated (2021-2025)": (g["value"].notna()).sum(),
                "MISSING_TAG (2026 pending)": (g["data_quality"] == "MISSING_TAG").sum(),
                "Tags Used": ", ".join(sorted(set(g["source_tag"].dropna().unique()))),
            })
        )
        .reset_index()
    )
    print(debt_summary.to_string(index=False))

    # 2. Sample of Tidy Ratio Table per Company
    print("\n" + "-" * 78)
    print("2. SAMPLE TIDY RATIO TABLE (2 rows per company)")
    print("-" * 78)
    sample_rows = (
        ratios_df.groupby("ticker")
        .apply(lambda g: g.head(2))
        .reset_index(drop=True)
    )
    display_cols = ["ticker", "cal_year", "ratio_category", "ratio_name", "value_formatted", "data_quality"]
    print(sample_rows[display_cols].to_string(index=False))

    # 3. Extreme / Outlier Ratios Audit Report
    print("\n" + "-" * 78)
    print("3. EXTREME / OUTLIER RATIOS AUDIT (Signal for Phase 4 & Memo)")
    print("-" * 78)
    outliers = []

    for _, r in ratios_df.iterrows():
        val = r["value"]
        if val is None or math.isnan(val) or math.isinf(val):
            continue

        r_name = r["ratio_name"]
        dq = r["data_quality"]
        flag_reason = None

        # Negative equity
        if "NEGATIVE_EQUITY" in dq:
            flag_reason = "Negative Equity Distortion"
        # Extreme leverage
        elif r_name == "debt_to_equity" and (val > 10.0 or val < 0):
            flag_reason = f"High/Distressed Leverage ({val:.2f}x)"
        # Distressed or extreme coverage
        elif r_name == "interest_coverage" and (abs(val) < 0.5 or val < 0):
            flag_reason = f"Near-Zero or Negative Coverage ({val:.2f}x)"
        # Extreme net margin
        elif r_name == "net_margin" and (abs(val) > 1.0):
            flag_reason = f"Extreme Margin ({val * 100:.1f}%)"
        # Extreme ROE
        elif r_name == "roe" and (abs(val) > 1.0):
            flag_reason = f"Extreme ROE ({val * 100:.1f}%)"

        if flag_reason:
            outliers.append({
                "Ticker": r["ticker"],
                "Year": r["cal_year"],
                "Ratio": r_name,
                "Value": r["value_formatted"],
                "Flag Reason": flag_reason,
                "Data Quality": dq,
            })

    if outliers:
        outlier_df = pd.DataFrame(outliers).drop_duplicates(subset=["Ticker", "Year", "Ratio"])
        print(f"Identified {len(outlier_df)} extreme/distressed ratio observations (retained for research signal):")
        print(outlier_df.to_string(index=False))
    else:
        print("No extreme ratios identified outside tolerance thresholds.")

    # 4. Overall Tidy Ratios Summary Matrix
    print("\n" + "-" * 78)
    print("4. RATIO STATUS MATRIX (BY TICKER)")
    print("-" * 78)
    matrix = (
        ratios_df.assign(
            status=ratios_df["value_formatted"].apply(
                lambda s: "CALCULATED" if not str(s).startswith("N/A") else "EXPLICIT_N/A"
            )
        )
        .pivot_table(index="ticker", columns="status", values="cal_year", aggfunc="count", fill_value=0)
    )
    matrix["TOTAL"] = matrix.sum(axis=1)
    print(matrix.to_string())
    print("=" * 78)


def main() -> None:
    args = parse_args()
    tickers = list(COMPANIES.keys()) if args.all else args.tickers

    logger.info(f"Starting Ratio Engine for: {tickers}")

    # Read normalized financials
    financials = read_financials()
    if financials.empty:
        logger.error("Financials table is empty. Run 'python run_ingestion.py --all' first.")
        sys.exit(1)

    # Filter to requested tickers if specified
    sub_financials = financials[financials["ticker"].isin(tickers)].copy()
    if sub_financials.empty:
        logger.error(f"No financials found for tickers: {tickers}")
        sys.exit(1)

    # Compute ratios
    ratios_df = compute_all_ratios(df_financials=sub_financials)

    if ratios_df.empty:
        logger.error("Ratio computation produced no data.")
        sys.exit(1)

    # Persist to SQLite and CSV
    write_ratios_to_sqlite(ratios_df)
    write_ratios_to_csv(ratios_df)

    logger.info(f"Ratio computation complete. Total rows: {len(ratios_df)}")

    # Display validation checkpoint
    display_validation_checkpoint(ratios_df, financials)

    if args.show_table:
        pd.set_option("display.max_rows", 200)
        pd.set_option("display.max_columns", 10)
        pd.set_option("display.width", 140)
        print("\n" + "=" * 78)
        print("FULL TIDY RATIOS TABLE")
        print("=" * 78)
        cols = ["ticker", "cal_year", "ratio_name", "value_formatted", "data_quality", "quality_note"]
        print(ratios_df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
