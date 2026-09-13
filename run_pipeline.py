"""
run_pipeline.py — End-to-End Orchestrator for the Automated Equity Research Desk.

Usage:
    python run_pipeline.py
    python run_pipeline.py --tickers AFRM UPST
    python run_pipeline.py --no-cache

Orchestrates the full 4-stage institutional equity research pipeline:
  Stage 1: SEC EDGAR Ingestion & Normalization (XBRL -> Tidy SQLite/CSV)
  Stage 2: Financial Ratio Engine (540 ratios across 10 core metrics)
  Stage 3: Adapted Forensic Anomaly Detection (Adapted Beneish M, Adapted Altman Z, Accruals, Divergence)
  Stage 4: Institutional Investment Memo & PDF Export (UPST 2-page note)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import COMPANIES
from run_ingestion import run_pipeline as run_ingestion_pipeline
from ingestion.store import read_financials
from ratios.ratio_engine import compute_all_ratios
from ratios.store import write_ratios_to_sqlite, write_ratios_to_csv, read_ratios
from ingestion.market_data import read_market_data
from anomaly.detector import compute_all_anomalies, audit_phase3_cross_correlation
from anomaly.store import write_anomalies_to_sqlite, write_anomalies_to_csv, read_anomalies
from memo.generate_memo import generate_memo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline_orchestrator")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Equity Research Desk — Full End-to-End Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=list(COMPANIES.keys()),
        help="Tickers to process (defaults to all 9 peer universe companies).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force fresh SEC EDGAR API downloads instead of using data/raw/ cache.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = args.tickers
    use_cache = not args.no_cache

    print("\n" + "=" * 80)
    print("  AUTOMATED EQUITY RESEARCH DESK — FULL PIPELINE EXECUTION")
    print(f"  Target Universe: {len(tickers)} companies ({', '.join(tickers)})")
    print(f"  Cache Mode: {'Enabled (Local)' if use_cache else 'Disabled (Fresh EDGAR pull)'}")
    print("=" * 80 + "\n")

    t0 = time.time()

    # -------------------------------------------------------------------------
    # STAGE 1: INGESTION & NORMALIZATION
    # -------------------------------------------------------------------------
    print(">>> [STAGE 1/4] SEC EDGAR Ingestion & GAAP/XBRL Normalization...")
    t_stage = time.time()
    fin_df = run_ingestion_pipeline(tickers=tickers, use_cache=use_cache)
    print(f"    [+] Ingested and normalized {len(fin_df)} facts in {time.time() - t_stage:.2f}s\n")

    # -------------------------------------------------------------------------
    # STAGE 2: RATIO ENGINE
    # -------------------------------------------------------------------------
    print(">>> [STAGE 2/4] Computing Financial Ratios (Profitability, Leverage, Liquidity)...")
    t_stage = time.time()
    ratios_df = compute_all_ratios(fin_df)
    write_ratios_to_sqlite(ratios_df)
    write_ratios_to_csv(ratios_df)
    print(f"    [+] Computed & stored {len(ratios_df)} ratio rows in {time.time() - t_stage:.2f}s\n")

    # -------------------------------------------------------------------------
    # STAGE 3: ADAPTED ANOMALY & FORENSIC MODULE
    # -------------------------------------------------------------------------
    print(">>> [STAGE 3/4] Running Adapted Forensic Models (Beneish M, Altman Z, Accruals)...")
    t_stage = time.time()
    mkt_df = read_market_data()
    anomalies_df = compute_all_anomalies(tickers, financials_df=fin_df, market_df=mkt_df)
    write_anomalies_to_sqlite(anomalies_df)
    write_anomalies_to_csv(anomalies_df)
    print(f"    [+] Computed {len(anomalies_df)} anomaly scores in {time.time() - t_stage:.2f}s\n")

    # -------------------------------------------------------------------------
    # STAGE 4: INVESTMENT MEMO & PDF EXPORT
    # -------------------------------------------------------------------------
    print(">>> [STAGE 4/5] Generating Institutional 2-Page Investment Memo (UPST)...")
    t_stage = time.time()
    generate_memo()
    print(f"    [+] Memo rendered to Markdown, HTML, and 2-Page PDF in {time.time() - t_stage:.2f}s\n")

    # -------------------------------------------------------------------------
    # STAGE 5: SQL SHOWCASE & TABLEAU BI EXPORT LAYER
    # -------------------------------------------------------------------------
    print(">>> [STAGE 5/5] Refreshing SQL Showcase & Tableau BI Export Layer...")
    t_stage = time.time()
    from sql.run_sql_showcase import run_showcase
    from data.exports.generate_tableau_export import build_tableau_export
    run_showcase()
    build_tableau_export()
    print(f"    [+] Generated 7 SQL queries and data/exports/tableau_export.csv in {time.time() - t_stage:.2f}s\n")

    elapsed = time.time() - t0
    print("=" * 80)
    print(f"  [+] PIPELINE EXECUTION COMPLETE in {elapsed:.2f} seconds!")
    print("  Artifacts ready:")
    print("    - Normalized Database: data/normalized/financials.db")
    print("    - Ratio Store:         data/normalized/ratios.csv")
    print("    - Anomaly Store:       data/normalized/anomalies.csv")
    print("    - UPST Investment Note: memo/UPST_investment_memo.md")
    print("    - UPST PDF Memo:       memo/UPST_investment_memo.pdf (Strict 2-Page)")
    print("    - SQL Showcase:        sql/README.md (7 Analytical Queries)")
    print("    - Tableau Export:      data/exports/tableau_export.csv (BI-Ready)")
    print("  To launch the interactive dashboard:")
    print("    streamlit run dashboard/app.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
