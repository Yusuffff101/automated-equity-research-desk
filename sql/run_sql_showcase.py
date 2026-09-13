"""
sql/run_sql_showcase.py — Execute all analytical SQL queries and generate sql/README.md.

Usage:
    python sql/run_sql_showcase.py

Runs 7 production analytical SQL queries directly against data/normalized/financials.db,
captures sample results, and formats them into sql/README.md with markdown tables.
"""

import os
import sqlite3
import sys
from pathlib import Path
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"
DB_PATH = PROJECT_ROOT / "data" / "normalized" / "financials.db"
OUTPUT_README = SQL_DIR / "README.md"

QUERY_METADATA = [
    {
        "file": "01_growth_divergence.sql",
        "title": "Query 1: Revenue vs. Receivables Growth Divergence",
        "question": "Which company-years experienced an abnormal decoupling between receivables buildup and revenue growth?",
        "technique": "CTEs + Window function LAG() OVER (PARTITION BY ticker ORDER BY cal_year)",
        "limit": 10,
    },
    {
        "file": "02_consecutive_distress_runs.sql",
        "title": "Query 2: Multi-Year Chronic Runs in the Altman Z Distress Zone",
        "question": "Which specialty lenders suffered chronic, multi-year runs in the Distress Zone (Z < 1.81) vs. cyclical fragility?",
        "technique": "Window functions LAG() & LEAD() detecting sequential distress states + GROUP_CONCAT",
        "limit": None,
    },
    {
        "file": "03_beneish_rankings.sql",
        "title": "Query 3: Peer Ranking by Forensic Earnings Manipulation Risk (Beneish M-Score)",
        "question": "How do companies rank across the peer group in earnings manipulation risk each calendar year?",
        "technique": "Window function DENSE_RANK() OVER (PARTITION BY cal_year ORDER BY score_value DESC)",
        "limit": 12,
    },
    {
        "file": "04_composite_risk_profile.sql",
        "title": "Query 4: Unified Multi-Table Risk Matrix (Ratios + Anomalies)",
        "question": "What is the cross-sectional risk profile for every company in the universe in FY2025?",
        "technique": "Multi-table CTEs joining `ratios` and `anomalies` on (ticker, cal_year) with composite tier logic",
        "limit": None,
    },
    {
        "file": "05_data_quality_audit.sql",
        "title": "Query 5: SEC EDGAR Data Quality & 10-K/A Restatement Audit",
        "question": "How are financial statement facts distributed across data quality flags, and which companies exhibit elevated 10-K/A restatement rates?",
        "technique": "Conditional aggregation COUNT(CASE WHEN ...) computing restatement percentages",
        "limit": None,
    },
    {
        "file": "06_relative_valuation_multiples.sql",
        "title": "Query 6: Cross-Sectional Relative Valuation Multiples (P/S, P/B, P/E)",
        "question": "What are the peer valuation multiples across the fintech universe in pure SQL, and how large is UPST's valuation premium?",
        "technique": "Multi-table JOIN between `market_data` and pivot CTE of `financials`",
        "limit": None,
    },
    {
        "file": "07_accruals_earnings_decoupling.sql",
        "title": "Query 7: Earnings Decoupling & Operating Cash Burn Audit",
        "question": "Which company-years exhibited deceptive accounting health—reporting positive GAAP net income while operating cash flow burned negative?",
        "technique": "Pivot CTE comparing Net Income against CFO and computing non-cash accruals magnitude",
        "limit": 10,
    },
    {
        "file": "08_memo_reconciliation.sql",
        "title": "Query 8: Investment Memo Longitudinal Reconciliation & Data Audit",
        "question": "How do the fundamental, leverage, and forensic metrics cited in the UPST institutional investment memo reconcile against canonical database truth?",
        "technique": "Multi-CTE join linking `financials`, `ratios`, `anomalies`, and `market_data` for audit verification",
        "limit": None,
    },
]


def run_showcase() -> None:
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    readme_content = [
        "# 🏛️ SQL Analytics Showcase: Automated Equity Research Desk",
        "",
        "This directory showcases **8 production analytical SQL queries** executed directly against the local SQLite warehouse ([`data/normalized/financials.db`](../data/normalized/financials.db)).",

        "",
        "Rather than trivial `SELECT *` filtering, each query addresses a specific fundamental research question using advanced SQL techniques: **window functions (`LAG`, `LEAD`, `DENSE_RANK`)**, **multi-table Common Table Expressions (CTEs)**, **conditional aggregation**, and **cross-table JOINs**.",
        "",
        "---",
        "",
        "## 📋 Query Index",
        "",
        "| Query | File | Analytical Theme | Advanced SQL Technique |",
        "|:---:|:---|:---|:---|",
    ]

    for i, meta in enumerate(QUERY_METADATA, 1):
        readme_content.append(
            f"| **{i}** | [`{meta['file']}`](./{meta['file']}) | {meta['title']} | {meta['technique']} |"
        )

    readme_content.append("\n---\n")

    print("\n" + "=" * 80)
    print("  EXECUTING SQL ANALYTICS SHOWCASE (financials.db)")
    print("=" * 80)

    for i, meta in enumerate(QUERY_METADATA, 1):
        sql_file = SQL_DIR / meta["file"]
        if not sql_file.exists():
            print(f"Warning: File {sql_file} not found. Skipping.")
            continue

        sql_text = sql_file.read_text(encoding="utf-8")
        print(f"\n[{i}/7] Running: {meta['file']}...")

        df = pd.read_sql_query(sql_text, conn)
        row_count = len(df)
        print(f"    ✓ Returned {row_count} rows.")

        readme_content.extend([
            f"## {meta['title']}",
            "",
            f"**File:** [`sql/{meta['file']}`](./{meta['file']})  ",
            f"**Analytical Objective:** {meta['question']}  ",
            f"**SQL Features:** `{meta['technique']}`  ",
            "",
            "### SQL Implementation",
            "```sql",
            sql_text.strip(),
            "```",
            "",
            f"### Query Results ({'Sample Top ' + str(meta['limit']) if meta['limit'] else f'All {row_count}'} Rows)",
            "",
        ])

        display_df = df.head(meta["limit"]) if meta["limit"] else df
        readme_content.append(display_df.to_markdown(index=False))
        readme_content.extend(["", "---", ""])

    conn.close()

    OUTPUT_README.write_text("\n".join(readme_content), encoding="utf-8")
    print("\n" + "=" * 80)
    print(f"  ✓ SQL SHOWCASE COMPLETE! Generated {OUTPUT_README}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_showcase()
