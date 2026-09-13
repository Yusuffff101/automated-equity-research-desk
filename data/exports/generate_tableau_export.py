"""
data/exports/generate_tableau_export.py — Generate BI-Ready Flat CSV for Tableau Public.

Usage:
    python data/exports/generate_tableau_export.py

Produces:
    data/exports/tableau_export.csv (54 company-year rows, 38 clean columns)
"""

import sqlite3
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "normalized" / "financials.db"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
EXPORT_CSV = EXPORTS_DIR / "tableau_export.csv"

# Company name mapping
COMPANY_NAMES = {
    "AFRM": "Affirm Holdings, Inc.",
    "SEZL": "Sezzle Inc.",
    "UPST": "Upstart Holdings, Inc.",
    "SOFI": "SoFi Technologies, Inc.",
    "LC": "LendingClub Corporation",
    "PGY": "Pagaya Technologies Ltd.",
    "OPRT": "Oportun Financial Corporation",
    "OMF": "OneMain Holdings, Inc.",
    "ENVA": "Enova International, Inc.",
}

SUBSECTOR_MAP = {
    "AFRM": "Buy Now Pay Later (BNPL)",
    "SEZL": "Buy Now Pay Later (BNPL)",
    "UPST": "AI Marketplace Lending",
    "SOFI": "Digital Banking & Consumer Credit",
    "LC": "Digital Banking & Personal Loans",
    "PGY": "AI Securitization & Partner Network",
    "OPRT": "Community & Subprime Lending",
    "OMF": "Installment Lending Franchise",
    "ENVA": "Digital Subprime & SMB Lending",
}


def build_tableau_export() -> None:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # 1. Base Company-Year Grid
    grid_query = """
    SELECT DISTINCT ticker, cik, cal_year
    FROM financials
    ORDER BY ticker, cal_year;
    """
    base_df = pd.read_sql_query(grid_query, conn)

    # Add descriptive company names & subsectors
    base_df["Company_Name"] = base_df["ticker"].map(COMPANY_NAMES)
    base_df["Subsector"] = base_df["ticker"].map(SUBSECTOR_MAP)

    # 2. Financials Pivoted ($M)
    fin_query = """
    SELECT 
        ticker,
        cal_year,
        MAX(fiscal_period_end) AS Fiscal_Period_End,
        ROUND(MAX(CASE WHEN line_item = 'revenue' THEN value END) / 1e6, 2) AS Revenue_M,
        ROUND(MAX(CASE WHEN line_item = 'net_income' THEN value END) / 1e6, 2) AS Net_Income_M,
        ROUND(MAX(CASE WHEN line_item = 'operating_cash_flow' THEN value END) / 1e6, 2) AS Operating_Cash_Flow_M,
        ROUND(MAX(CASE WHEN line_item = 'total_assets' THEN value END) / 1e6, 2) AS Total_Assets_M,
        ROUND(MAX(CASE WHEN line_item = 'total_liabilities' THEN value END) / 1e6, 2) AS Total_Liabilities_M,
        ROUND(MAX(CASE WHEN line_item = 'shareholders_equity' THEN value END) / 1e6, 2) AS Shareholders_Equity_M,
        ROUND(MAX(CASE WHEN line_item = 'total_debt' THEN value END) / 1e6, 2) AS Total_Debt_M,
        ROUND(MAX(CASE WHEN line_item = 'cash_and_equivalents' THEN value END) / 1e6, 2) AS Cash_And_Equivalents_M,
        ROUND(MAX(CASE WHEN line_item = 'ebit' THEN value END) / 1e6, 2) AS EBIT_M,
        ROUND(MAX(CASE WHEN line_item = 'interest_expense' THEN value END) / 1e6, 2) AS Interest_Expense_M,
        ROUND(MAX(CASE WHEN line_item = 'receivables' THEN value END) / 1e6, 2) AS Receivables_M,
        ROUND(MAX(CASE WHEN line_item = 'retained_earnings' THEN value END) / 1e6, 2) AS Retained_Earnings_M,
        COUNT(CASE WHEN data_quality = 'RESTATED' THEN 1 END) AS Restated_Fact_Count,
        COUNT(CASE WHEN data_quality = 'COMPARATIVE' THEN 1 END) AS Comparative_Fact_Count,
        COUNT(CASE WHEN data_quality = 'MISSING_TAG' THEN 1 END) AS Missing_Tag_Count
    FROM financials
    GROUP BY ticker, cal_year;
    """
    fin_df = pd.read_sql_query(fin_query, conn)

    # 3. Ratios Pivoted
    ratios_query = """
    SELECT
        ticker,
        cal_year,
        ROUND(MAX(CASE WHEN ratio_name = 'roe' THEN value END) * 100, 2) AS ROE_Pct,
        ROUND(MAX(CASE WHEN ratio_name = 'roa' THEN value END) * 100, 2) AS ROA_Pct,
        ROUND(MAX(CASE WHEN ratio_name = 'net_margin' THEN value END) * 100, 2) AS Net_Margin_Pct,
        ROUND(MAX(CASE WHEN ratio_name = 'debt_to_equity' THEN value END), 2) AS Debt_To_Equity_Mult,
        ROUND(MAX(CASE WHEN ratio_name = 'interest_coverage' THEN value END), 2) AS Interest_Coverage_Mult,
        ROUND(MAX(CASE WHEN ratio_name = 'asset_turnover' THEN value END), 3) AS Asset_Turnover_Mult,
        ROUND(MAX(CASE WHEN ratio_name = 'receivables_turnover' THEN value END), 2) AS Receivables_Turnover_Mult
    FROM ratios
    GROUP BY ticker, cal_year;
    """
    ratios_df = pd.read_sql_query(ratios_query, conn)

    # 4. Anomalies Pivoted
    anom_query = """
    SELECT
        ticker,
        cal_year,
        ROUND(MAX(CASE WHEN anomaly_name = 'adapted_altman_z_score' THEN score_value END), 2) AS Adapted_Altman_Z_Score,
        MAX(CASE WHEN anomaly_name = 'adapted_altman_z_score' THEN classification END) AS Altman_Z_Classification,
        ROUND(MAX(CASE WHEN anomaly_name = 'adapted_beneish_m_score' THEN score_value END), 2) AS Adapted_Beneish_M_Score,
        MAX(CASE WHEN anomaly_name = 'adapted_beneish_m_score' THEN classification END) AS Beneish_M_Classification,
        ROUND(MAX(CASE WHEN anomaly_name = 'accruals_ratio' THEN score_value END), 3) AS Accruals_Ratio,
        MAX(CASE WHEN anomaly_name = 'accruals_ratio' THEN classification END) AS Accruals_Classification,
        ROUND(MAX(CASE WHEN anomaly_name = 'growth_divergence' THEN score_value END), 2) AS Growth_Divergence_Pct,
        MAX(CASE WHEN anomaly_name = 'growth_divergence' THEN classification END) AS Growth_Divergence_Classification
    FROM anomalies
    GROUP BY ticker, cal_year;
    """
    anom_df = pd.read_sql_query(anom_query, conn)

    # Add methodology labels for Tableau tooltip reference
    anom_df["Altman_Z_Methodology"] = "Adapted Z-Score (Cash/TA substitution for unclassified balance sheets)"
    anom_df["Beneish_M_Methodology"] = "Adapted M-Score (ex-GMI financial institution adjustment)"
    anom_df["Accruals_Methodology"] = "Sloan Accruals: (Net Income - Operating Cash Flow) / Total Assets"

    # 5. Market Data & Multiples
    mkt_query = """
    SELECT
        ticker,
        cal_year,
        ROUND(close_price, 2) AS Close_Price,
        ROUND(shares_outstanding / 1e6, 2) AS Shares_Outstanding_M,
        ROUND(market_cap / 1e6, 2) AS Market_Cap_M,
        is_pre_ipo AS Is_Pre_IPO
    FROM market_data;
    """
    mkt_df = pd.read_sql_query(mkt_query, conn)

    conn.close()

    # 6. Merge All Modules
    merged = base_df.merge(fin_df, on=["ticker", "cal_year"], how="left")
    merged = merged.merge(ratios_df, on=["ticker", "cal_year"], how="left")
    merged = merged.merge(anom_df, on=["ticker", "cal_year"], how="left")
    merged = merged.merge(mkt_df, on=["ticker", "cal_year"], how="left")

    # 7. Compute Valuation Multiples
    # P/S = Market_Cap / Revenue
    merged["PS_Multiple"] = np.where(
        merged["Revenue_M"] > 0,
        np.round(merged["Market_Cap_M"] / merged["Revenue_M"], 2),
        np.nan,
    )
    # P/B = Market_Cap / Equity
    merged["PB_Multiple"] = np.where(
        merged["Shareholders_Equity_M"] > 0,
        np.round(merged["Market_Cap_M"] / merged["Shareholders_Equity_M"], 2),
        np.nan,
    )
    # P/E = Market_Cap / Net_Income (positive net income only)
    merged["PE_Multiple"] = np.where(
        merged["Net_Income_M"] > 0,
        np.round(merged["Market_Cap_M"] / merged["Net_Income_M"], 2),
        np.nan,
    )

    # 8. Create Data Quality Summary Column for Tableau Tooltips
    def build_quality_summary(row):
        parts = []
        if row["Restated_Fact_Count"] > 0:
            parts.append(f"{int(row['Restated_Fact_Count'])} facts restated (10-K/A)")
        if row["Comparative_Fact_Count"] > 0:
            parts.append(f"{int(row['Comparative_Fact_Count'])} comparative facts")
        if row["Missing_Tag_Count"] > 0:
            parts.append(f"{int(row['Missing_Tag_Count'])} missing tags")
        if row["Is_Pre_IPO"] == 1:
            parts.append("Pre-IPO period")
        return "; ".join(parts) if parts else "OK (Primary XBRL tags)"

    merged["Data_Quality_Summary"] = merged.apply(build_quality_summary, axis=1)

    # Rename & reorder columns for optimal Tableau drag-and-drop experience
    col_order = [
        "ticker", "Company_Name", "cik", "Subsector", "cal_year", "Fiscal_Period_End",
        "Revenue_M", "Net_Income_M", "Operating_Cash_Flow_M", "Total_Assets_M",
        "Total_Liabilities_M", "Shareholders_Equity_M", "Total_Debt_M",
        "Cash_And_Equivalents_M", "EBIT_M", "Interest_Expense_M", "Receivables_M",
        "Retained_Earnings_M",
        "ROE_Pct", "ROA_Pct", "Net_Margin_Pct", "Debt_To_Equity_Mult",
        "Interest_Coverage_Mult", "Asset_Turnover_Mult", "Receivables_Turnover_Mult",
        "Adapted_Altman_Z_Score", "Altman_Z_Classification", "Altman_Z_Methodology",
        "Adapted_Beneish_M_Score", "Beneish_M_Classification", "Beneish_M_Methodology",
        "Accruals_Ratio", "Accruals_Classification", "Accruals_Methodology",
        "Growth_Divergence_Pct", "Growth_Divergence_Classification",
        "Close_Price", "Shares_Outstanding_M", "Market_Cap_M",
        "PS_Multiple", "PB_Multiple", "PE_Multiple", "Is_Pre_IPO",
        "Restated_Fact_Count", "Comparative_Fact_Count", "Missing_Tag_Count",
        "Data_Quality_Summary"
    ]
    # Rename ticker -> Ticker, cik -> CIK, cal_year -> Calendar_Year
    rename_dict = {
        "ticker": "Ticker",
        "cik": "CIK",
        "cal_year": "Calendar_Year",
    }
    merged = merged.rename(columns=rename_dict)
    col_order = [rename_dict.get(c, c) for c in col_order]
    final_df = merged[col_order]

    # Save to CSV
    final_df.to_csv(EXPORT_CSV, index=False, encoding="utf-8")
    print(f"\n[+] Successfully exported Tableau-ready CSV:")
    print(f"    File:  {EXPORT_CSV}")
    print(f"    Shape: {final_df.shape[0]} rows x {final_df.shape[1]} columns")
    print(f"    Grain: Ticker x Calendar_Year (54 total company-years)\n")


if __name__ == "__main__":
    build_tableau_export()
