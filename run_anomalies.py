"""
run_anomalies.py — CLI entry point for the Anomaly & Red-Flag Detection Module.

Usage:
    # Compute and persist anomaly scores for all 9 companies:
    python run_anomalies.py --all

    # Compute for specific companies:
    python run_anomalies.py --tickers AFRM PGY SEZL

    # Display full anomaly table in terminal:
    python run_anomalies.py --all --show-table
"""

import argparse
import logging
import math
import sys
from pathlib import Path
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


from config import COMPANIES
from ingestion.store import read_financials
from ingestion.market_data import read_market_data
from ratios.store import read_ratios
from anomaly.detector import (
    compute_all_anomalies,
    audit_phase3_cross_correlation,
)
from anomaly.store import (
    write_anomalies_to_sqlite,
    write_anomalies_to_csv,
    read_anomalies,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_anomalies")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Equity Research Desk — Anomaly & Red-Flag Detection Module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Compute anomaly scores for all 9 companies in the universe.",
    )
    group.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="One or more tickers to process (e.g. AFRM PGY SEZL).",
    )
    parser.add_argument(
        "--show-table",
        action="store_true",
        help="Print the full anomaly table to stdout.",
    )
    return parser.parse_args()


def display_validation_checkpoint(
    anomalies_df: pd.DataFrame,
    ratios_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> None:
    """Print the required validation checkpoint sections."""
    print("\n" + "=" * 92)
    print("PHASE 4 VALIDATION CHECKPOINT: ANOMALY & RED-FLAG DETECTION MODULE")
    print("=" * 92)

    # --------------------------------------------------------------------------
    # 1. Adapted M-Score and Z-Score for All 9 Companies with Explanations
    # --------------------------------------------------------------------------
    print("\n" + "-" * 92)
    print("1. ADAPTED BENEISH M-SCORE & ALTMAN Z-SCORE (SAMPLE BY COMPANY WITH EXPLANATIONS)")
    print("-" * 92)

    mz_scores = anomalies_df[anomalies_df["anomaly_name"].isin(["adapted_beneish_m_score", "adapted_altman_z_score"])]
    
    # Show representative recent periods (e.g. 2023 or 2024) across each company
    for ticker in sorted(anomalies_df["ticker"].unique()):
        t_mz = mz_scores[mz_scores["ticker"] == ticker]
        print(f"\n[{ticker}] — {COMPANIES.get(ticker, {}).get('name', ticker)}")
        for _, row in t_mz.iterrows():
            yr = row["cal_year"]
            model = "M-Score" if "beneish" in row["anomaly_name"] else "Z-Score"
            score_str = row["score_formatted"]
            cls = row["classification"]
            exp = row["explanation"]
            print(f"  {yr} | {model:7s} | {score_str:28s} | [{cls:24s}]")
            print(f"       -> {exp}")

    # --------------------------------------------------------------------------
    # 2. Distress Zone vs. Grey Zone vs. Safe Zone Distribution
    # --------------------------------------------------------------------------
    print("\n" + "-" * 92)
    print("2. DISTRESS ZONE VS. GREY ZONE VS. SAFE ZONE DISTRIBUTION (ALTMAN Z-SCORE)")
    print("-" * 92)

    z_scores = anomalies_df[anomalies_df["anomaly_name"] == "adapted_altman_z_score"]
    z_dist = (
        z_scores.pivot_table(
            index="ticker",
            columns="classification",
            values="cal_year",
            aggfunc="count",
            fill_value=0,
        )
    )
    for col in ["DISTRESS_ZONE", "GREY_ZONE", "SAFE_ZONE", "PRE_IPO_UNAVAILABLE", "MISSING_DATA"]:
        if col not in z_dist.columns:
            z_dist[col] = 0
    z_dist = z_dist[["DISTRESS_ZONE", "GREY_ZONE", "SAFE_ZONE", "PRE_IPO_UNAVAILABLE", "MISSING_DATA"]]
    z_dist["TOTAL_PERIODS"] = z_dist.sum(axis=1)
    print(z_dist.to_string())


    print("\n" + "-" * 92)
    print("BENEISH M-SCORE RISK DISTRIBUTION")
    print("-" * 92)
    m_scores = anomalies_df[anomalies_df["anomaly_name"] == "adapted_beneish_m_score"]
    m_dist = (
        m_scores.pivot_table(

            index="ticker",
            columns="classification",
            values="cal_year",
            aggfunc="count",
            fill_value=0,
        )
    )
    m_cols = ["LOW_MANIPULATION_RISK", "ELEVATED_MANIPULATION_RISK", "INSUFFICIENT_HISTORY", "MISSING_DATA"]
    for col in m_cols:
        if col not in m_dist.columns:
            m_dist[col] = 0
    m_dist = m_dist[m_cols]
    m_dist["TOTAL_PERIODS"] = m_dist.sum(axis=1)
    print(m_dist.to_string())



    # --------------------------------------------------------------------------
    # 3. Cross-Correlation Audit Against Phase 3's 17 Distress Outliers
    # --------------------------------------------------------------------------
    print("\n" + "-" * 92)
    print("3. PHASE 3 OUTLIER CROSS-CORRELATION AUDIT (17 HISTORICAL DISTRESS SIGNALS)")
    print("-" * 92)

    corr_df = audit_phase3_cross_correlation(anomalies_df, ratios_df)
    if not corr_df.empty:
        display_corr = corr_df[[
            "ticker", "cal_year", "phase3_outlier_reason", "adapted_z_score", "z_zone", "correlation_signal"
        ]]
        print(display_corr.to_string(index=False))
        
        print("\nDeep-Dive on Key Corporate Outliers:")
        # Highlight PGY and SEZL specifically
        pgy_2024 = anomalies_df[(anomalies_df["ticker"] == "PGY") & (anomalies_df["cal_year"] == 2024)]
        print("\n* Pagaya (PGY) 2024 Restatement (10-K/A & -123% ROE):")
        for _, r in pgy_2024.iterrows():
            print(f"    - {r['anomaly_name']}: {r['score_formatted']} [{r['classification']}]")
            print(f"      {r['explanation']}")

        sezl_distress = anomalies_df[(anomalies_df["ticker"] == "SEZL") & (anomalies_df["cal_year"].isin([2021, 2022]))]
        print("\n* Sezzle (SEZL) 2021-2022 Negative Equity & Venture Burn:")
        for _, r in sezl_distress.iterrows():
            if r["anomaly_name"] in ("adapted_altman_z_score", "accruals_ratio"):
                print(f"    - {r['cal_year']} {r['anomaly_name']}: {r['score_formatted']} [{r['classification']}]")
                print(f"      {r['explanation']}")

    # --------------------------------------------------------------------------
    # 4. Confirmation of IPO-Timing Graceful Handling
    # --------------------------------------------------------------------------
    print("\n" + "-" * 92)
    print("4. CONFIRMATION OF IPO-TIMING GRACEFUL HANDLING")
    print("-" * 92)
    ipo_audit = market_df[market_df["data_quality"].isin(["PRE_IPO_UNAVAILABLE", "INCOMPLETE_SHARES"])]
    if not ipo_audit.empty:
        print("Identified pre-IPO / non-trading periods in market dataset (no private valuations fabricated):")
        print(ipo_audit[["ticker", "cal_year", "fiscal_period_end", "data_quality", "is_pre_ipo"]].to_string(index=False))
    else:
        print("All records populated with post-IPO market data.")

    # --------------------------------------------------------------------------
    # 5. Domain Rules & Exemption Verification (PGY & ENVA Growth Divergence)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 92)
    print("5. DOMAIN RULE EXEMPTION: REVENUE VS. RECEIVABLES GROWTH DIVERGENCE (PGY & ENVA)")
    print("-" * 92)
    div_df = anomalies_df[anomalies_df["anomaly_name"] == "growth_divergence"]
    for t in ["PGY", "ENVA", "AFRM", "UPST"]:
        sample = div_df[div_df["ticker"] == t].head(1)
        if not sample.empty:
            r = sample.iloc[0]
            print(f"[{t}] {r['cal_year']}: {r['score_formatted']} | [{r['classification']}]")
            print(f"     Explanation: {r['explanation']}")

    print("=" * 92 + "\n")


def main() -> None:
    args = parse_args()
    tickers = list(COMPANIES.keys()) if args.all else args.tickers

    logger.info(f"Running Anomaly Detection for {len(tickers)} companies: {', '.join(tickers)}")

    # 1. Load inputs
    financials_df = read_financials()
    market_df = read_market_data()
    ratios_df = read_ratios()

    # 2. Compute anomalies
    anomalies_df = compute_all_anomalies(tickers, financials_df=financials_df, market_df=market_df)

    if anomalies_df.empty:
        logger.error("No anomaly rows were generated. Exiting.")
        sys.exit(1)

    # 3. Persist
    write_anomalies_to_sqlite(anomalies_df)
    write_anomalies_to_csv(anomalies_df)

    logger.info(f"Successfully generated and stored {len(anomalies_df)} anomaly records.")

    # 4. Display validation checkpoint
    display_validation_checkpoint(anomalies_df, ratios_df, market_df)

    # 5. Optional full table display
    if args.show_table:
        print("\n--- FULL ANOMALY TABLE ---")
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 1000)
        print(anomalies_df[["ticker", "cal_year", "anomaly_name", "score_formatted", "classification", "explanation"]].to_string(index=False))


if __name__ == "__main__":
    main()
