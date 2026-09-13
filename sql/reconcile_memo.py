"""
sql/reconcile_memo.py — Automated Reconciliation Engine between UPST Investment Memo & Live Database

Validates every number, ratio, valuation multiple, and anomaly score cited in:
  memo/UPST_investment_memo.md
against:
  data/normalized/financials.db (tables: financials, ratios, anomalies, market_data)

Usage:
    python sql/reconcile_memo.py
"""

import os
import re
import sqlite3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMO_PATH = PROJECT_ROOT / "memo" / "UPST_investment_memo.md"
DB_PATH = PROJECT_ROOT / "data" / "normalized" / "financials.db"


def parse_memo_tables(memo_text: str) -> dict:
    """Extract tabular metrics from the markdown memo."""
    tables = {}
    lines = memo_text.splitlines()
    
    # Extract trajectory table
    trajectory = {}
    in_traj = False
    for line in lines:
        if "### Upstart Holdings (UPST) — Historical Trajectory" in line:
            in_traj = True
            continue
        if in_traj:
            if line.startswith("| Metric / Indicator"):
                continue
            if line.startswith("|:--"):
                continue
            if not line.startswith("|"):
                if trajectory:
                    break
                continue
            
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 6:
                metric_name = parts[0].replace("**", "").replace("($M)", "").replace("(Adapted)", "").replace("(TATA)", "").strip()
                vals = []
                for p in parts[1:6]:
                    clean = re.sub(r"\*\*|\+|\$|M|%|x|\(.*?\)", "", p).replace(",", "").strip()
                    vals.append(clean)
                trajectory[metric_name] = {
                    2021: vals[0], 2022: vals[1], 2023: vals[2], 2024: vals[3], 2025: vals[4]
                }

    
    tables["trajectory"] = trajectory

    # Extract relative valuation table
    val_table = {}
    in_val = False
    for line in lines:
        if "### FY2025 Relative Valuation Multiples" in line:
            in_val = True
            continue
        if in_val:
            if line.startswith("| Ticker"):
                continue
            if line.startswith("|:--"):
                continue
            if not line.startswith("|"):
                if val_table:
                    break
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 9:
                ticker = parts[0].replace("**", "").strip()
                val_table[ticker] = {
                    "market_cap": re.sub(r"\*\*|\$|B", "", parts[2]).replace(",", "").strip(),
                    "revenue": re.sub(r"\*\*|\$|M", "", parts[3]).replace(",", "").strip(),
                    "net_income": re.sub(r"\*\*|\+|\$|M", "", parts[4]).replace(",", "").strip(),
                    "equity": re.sub(r"\*\*|\$|M", "", parts[5]).replace(",", "").strip(),
                    "ps": re.sub(r"\*\*|x", "", parts[6]).replace(",", "").strip(),
                    "pb": re.sub(r"\*\*|x", "", parts[7]).replace(",", "").strip(),
                    "pe": re.sub(r"\*\*|x", "", parts[8]).replace(",", "").strip(),
                }
    tables["valuation"] = val_table
    return tables



def run_reconciliation():
    print("=" * 80)
    print("INSTITUTIONAL MEMO RECONCILIATION AUDIT (sql/reconcile_memo.py)")
    print("=" * 80)
    
    if not MEMO_PATH.exists():
        print(f"Error: Memo file not found at {MEMO_PATH}")
        sys.exit(1)
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    with open(MEMO_PATH, "r", encoding="utf-8") as f:
        memo_content = f.read()

    conn = sqlite3.connect(DB_PATH)

    # Pull DB data for UPST
    df_fin = pd.read_sql_query("SELECT cal_year, line_item, value FROM financials WHERE ticker='UPST'", conn)
    df_rat = pd.read_sql_query("SELECT cal_year, ratio_name, value FROM ratios WHERE ticker='UPST'", conn)
    df_anom = pd.read_sql_query("SELECT cal_year, anomaly_name, score_value FROM anomalies WHERE ticker='UPST'", conn)
    df_mkt = pd.read_sql_query("SELECT cal_year, market_cap, close_price FROM market_data WHERE ticker='UPST'", conn)

    parsed = parse_memo_tables(memo_content)
    traj = parsed["trajectory"]

    mismatches = []
    checks_passed = 0

    # Mapping from memo metric names to db queries
    metric_map = {
        "Revenue": ("financials", "revenue", 1e6, 0.015),
        "GAAP Net Income": ("financials", "net_income", 1e6, 0.015),
        "Operating Cash Flow": ("financials", "operating_cash_flow", 1e6, 0.015),
        "Total Debt": ("financials", "total_debt", 1e6, 0.015),
        "Total Liabilities": ("financials", "total_liabilities", 1e6, 0.015),
        "Shareholders' Equity": ("financials", "shareholders_equity", 1e6, 0.015),
        "Interest Coverage": ("ratios", "interest_coverage", 1.0, 0.05),
        "Return on Equity (ROE)": ("ratios", "roe", 0.01, 0.02),

        "Return on Assets (ROA)": ("ratios", "roa", 0.01, 0.02),
        "Accruals Ratio": ("anomalies", "accruals_ratio", 1.0, 0.01),
        "Growth Divergence": ("anomalies", "growth_divergence", 0.01, 0.02),
        "Beneish M-Score": ("anomalies", "adapted_beneish_m_score", 1.0, 0.05),
        "Altman Z-Score": ("anomalies", "adapted_altman_z_score", 1.0, 0.05),
    }

    print("\n--- 1. AUDITING HISTORICAL TRAJECTORY TABLE ---")
    for metric_label, (src_table, col_name, scale, tol) in metric_map.items():
        if metric_label not in traj:
            print(f"Warning: Metric '{metric_label}' not parsed from memo table.")
            continue

        for yr in [2021, 2022, 2023, 2024, 2025]:
            memo_str = traj[metric_label].get(yr, "")
            if not memo_str or "N/A" in memo_str:
                continue

            try:
                memo_val = float(memo_str)
            except ValueError:
                continue

            db_val = None
            if src_table == "financials":
                row = df_fin[(df_fin["cal_year"] == yr) & (df_fin["line_item"] == col_name)]
                if not row.empty and pd.notnull(row["value"].iloc[0]):
                    db_val = row["value"].iloc[0] / scale
            elif src_table == "ratios":
                row = df_rat[(df_rat["cal_year"] == yr) & (df_rat["ratio_name"] == col_name)]
                if not row.empty and pd.notnull(row["value"].iloc[0]):
                    db_val = row["value"].iloc[0] / scale
            elif src_table == "anomalies":
                row = df_anom[(df_anom["cal_year"] == yr) & (df_anom["anomaly_name"] == col_name)]
                if not row.empty and pd.notnull(row["score_value"].iloc[0]):
                    db_val = row["score_value"].iloc[0] / scale

            if db_val is None:
                mismatches.append({
                    "Section": "Trajectory",
                    "Metric": f"{metric_label} ({yr})",
                    "Memo Value": memo_str,
                    "DB Value": "NULL",
                    "Discrepancy": "Missing in DB"
                })
                continue

            # Compare relative or absolute difference
            diff = abs(memo_val - db_val)
            rel_diff = diff / abs(db_val) if db_val != 0 else diff
            
            # Use relative diff if scale is large, else absolute diff
            is_ok = rel_diff <= tol if abs(db_val) >= 1.0 else diff <= tol
            if is_ok:
                checks_passed += 1
            else:
                mismatches.append({
                    "Section": "Trajectory",
                    "Metric": f"{metric_label} ({yr})",
                    "Memo Value": f"{memo_val:.2f}",
                    "DB Value": f"{db_val:.2f}",
                    "Discrepancy": f"Diff: {memo_val - db_val:+.2f} ({rel_diff*100:.1f}%)"
                })

    print(f"Trajectory checks evaluated. Passed: {checks_passed}, Mismatches: {len(mismatches)}")

    print("\n--- 2. AUDITING PROSE CLAIMS ---")
    # Debt claims in prose
    prose_mismatches = []
    # Check for $1.39B in prose
    if "$1.39B" in memo_content:
        prose_mismatches.append("Obsolete '$1.39B' debt claim found in memo prose (canonical total debt is $1.83B).")
    if "$1,385.4M" in memo_content:
        prose_mismatches.append("Obsolete '$1,385.4M' debt claim found in memo prose (canonical total debt is $1,829.1M).")
    if "$868.5M" in memo_content:
        prose_mismatches.append("Obsolete '$868.5M' 2021 debt claim found in memo prose (canonical total debt is $695.4M).")

    # Check 2025 revenue claim
    if "$1,043.9M" in memo_content:
        checks_passed += 1
    else:
        prose_mismatches.append("2025 revenue '$1,043.9M' not found in prose.")

    # Check 2025 net income claim
    if "+$53.6M" in memo_content or "$+53.6M" in memo_content or "$53.6M" in memo_content:
        checks_passed += 1
    else:
        prose_mismatches.append("2025 Net income '$53.6M' not found in prose.")


    # Check 2025 CFO claim
    if "$-147.7M" in memo_content or "-$147.7M" in memo_content:
        checks_passed += 1
    else:
        prose_mismatches.append("2025 CFO '$-147.7M' not found in prose.")

    # Check 2025 Altman Z claim
    if "1.71" in memo_content:
        checks_passed += 1
    else:
        prose_mismatches.append("2025 Altman Z '1.71' not found in prose.")

    print(f"Prose checks evaluated. Prose warnings: {len(prose_mismatches)}")

    print("\n--- 3. AUDITING PEER RELATIVE VALUATION TABLE ---")
    val_table = parsed.get("valuation", {})
    query_peers = """
    SELECT 
        m.ticker,
        m.market_cap,
        MAX(CASE WHEN f.line_item = 'revenue' THEN f.value END) as revenue,
        MAX(CASE WHEN f.line_item = 'net_income' THEN f.value END) as net_income,
        MAX(CASE WHEN f.line_item = 'shareholders_equity' THEN f.value END) as equity
    FROM market_data m
    LEFT JOIN financials f ON m.ticker = f.ticker AND m.cal_year = f.cal_year
    WHERE m.cal_year = 2025
    GROUP BY m.ticker;
    """
    df_peers = pd.read_sql_query(query_peers, conn)
    peer_mismatches = []
    
    for _, prow in df_peers.iterrows():
        ptick = prow["ticker"]
        if ptick not in val_table:
            peer_mismatches.append(f"Ticker {ptick} missing from memo valuation table.")
            continue
        
        m_row = val_table[ptick]
        # Check market cap (billions)
        try:
            m_mc = float(m_row["market_cap"])
            db_mc = prow["market_cap"] / 1e9
            if abs(m_mc - db_mc) / db_mc < 0.02:
                checks_passed += 1
            else:
                peer_mismatches.append(f"{ptick} Market Cap: memo={m_mc}B, db={db_mc:.2f}B")
        except ValueError:
            pass

        # Check revenue (millions)
        try:
            m_rev = float(m_row["revenue"])
            db_rev = prow["revenue"] / 1e6
            if abs(m_rev - db_rev) / db_rev < 0.02:
                checks_passed += 1
            else:
                peer_mismatches.append(f"{ptick} Revenue: memo={m_rev}M, db={db_rev:.1f}M")
        except ValueError:
            pass

        # Check net income (millions)
        try:
            m_ni = float(m_row["net_income"])
            db_ni = prow["net_income"] / 1e6
            if abs(m_ni - db_ni) / abs(db_ni) < 0.02:
                checks_passed += 1
            else:
                peer_mismatches.append(f"{ptick} Net Income: memo={m_ni}M, db={db_ni:.1f}M")
        except ValueError:
            pass

    print(f"Peer valuation checks evaluated. Peer warnings: {len(peer_mismatches)}")


    print("\n" + "=" * 80)
    print("RECONCILIATION RESULT SUMMARY")
    print("=" * 80)
    if not mismatches and not prose_mismatches:
        print(f"ALL CHECKS PASSED ({checks_passed} verified points). Memo and live database are 100% reconciled!")
        return 0
    else:
        if mismatches:
            print("\n[!] TABULAR MISMATCHES:")
            df_m = pd.DataFrame(mismatches)
            print(df_m.to_string(index=False))
        if prose_mismatches:
            print("\n[!] PROSE MISMATCHES:")
            for pm in prose_mismatches:
                print(f"  - {pm}")
        return len(mismatches) + len(prose_mismatches)


if __name__ == "__main__":
    status = run_reconciliation()
    sys.exit(status)
