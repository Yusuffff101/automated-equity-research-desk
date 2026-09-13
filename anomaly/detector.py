"""
anomaly/detector.py — Orchestrator for Anomaly & Red-Flag Detection.

Coordinates:
  1. Adapted Beneish M-Score (ex-GMI financial adjustment)
  2. Adapted Altman Z-Score (Cash/TA substitution, MVE/TL from market data)
  3. Balance-Sheet Accruals Ratio ((NI - CFO) / Total Assets)
  4. Revenue vs. Receivables Growth Divergence (with PGY & ENVA explicit exemption)

Also provides:
  - Cross-correlation analysis against Phase 3's 17 distress outliers.
  - Anomaly distribution summaries (Distress vs. Grey vs. Safe zones).
  - IPO-timing graceful handling audit.
"""

import logging
import math
from typing import Optional, Any
import pandas as pd

from config import COMPANIES
from ingestion.store import read_financials
from ingestion.market_data import read_market_data
from anomaly.beneish import compute_adapted_beneish_for_company
from anomaly.altman import compute_adapted_altman_for_company
from anomaly.accruals import compute_accruals_for_company
from anomaly.divergence import compute_divergence_for_company

logger = logging.getLogger(__name__)


def compute_anomalies_for_company(
    ticker: str,
    cik: str,
    df_comp: pd.DataFrame,
    df_mkt: pd.DataFrame,
) -> list[dict]:
    """Run all 4 anomaly models for a single company across calendar years."""
    all_rows: list[dict] = []

    # 1. Adapted Beneish M-Score
    m_rows = compute_adapted_beneish_for_company(ticker, cik, df_comp)
    all_rows.extend(m_rows)

    # 2. Adapted Altman Z-Score
    z_rows = compute_adapted_altman_for_company(ticker, cik, df_comp, df_mkt)
    all_rows.extend(z_rows)

    # 3. Accruals Ratio
    acc_rows = compute_accruals_for_company(ticker, cik, df_comp)
    all_rows.extend(acc_rows)

    # 4. Revenue vs. Receivables Growth Divergence
    div_rows = compute_divergence_for_company(ticker, cik, df_comp)
    all_rows.extend(div_rows)

    return all_rows


def compute_all_anomalies(
    tickers: Optional[list[str]] = None,
    financials_df: Optional[pd.DataFrame] = None,
    market_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Compute all anomaly records for the specified universe (or all 9 companies)."""
    if financials_df is None:
        financials_df = read_financials()
    if market_df is None:
        market_df = read_market_data()

    if tickers is None:
        tickers = list(COMPANIES.keys())

    records: list[dict] = []
    for ticker in tickers:
        if ticker not in COMPANIES:
            logger.warning(f"Ticker '{ticker}' not found in universe config — skipping.")
            continue

        cik = COMPANIES[ticker]["cik"]
        df_comp = financials_df[financials_df["ticker"] == ticker]
        if df_comp.empty:
            logger.warning(f"No financial rows found for ticker '{ticker}' — skipping.")
            continue

        company_rows = compute_anomalies_for_company(ticker, cik, df_comp, market_df)
        records.extend(company_rows)

    df_anomalies = pd.DataFrame(records)
    if df_anomalies.empty:
        return df_anomalies

    # Ensure standard column order
    cols_order = [
        "ticker", "cik", "cal_year", "fiscal_period_end",
        "anomaly_name", "score_value", "score_formatted",
        "classification", "explanation",
    ]
    # Retain any auxiliary model columns at the end
    extra_cols = [c for c in df_anomalies.columns if c not in cols_order]
    return df_anomalies[cols_order + extra_cols].sort_values(["ticker", "cal_year", "anomaly_name"]).reset_index(drop=True)


def extract_phase3_outliers(ratios_df: pd.DataFrame) -> pd.DataFrame:
    """Identify the 17 distress/extreme ratio observations from Phase 3."""
    outliers = []
    for _, r in ratios_df.iterrows():
        val = r["value"]
        if val is None or math.isnan(val) or math.isinf(val):
            continue

        r_name = r["ratio_name"]
        dq = r.get("data_quality", "")
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
                "ticker": r["ticker"],
                "cal_year": int(r["cal_year"]),
                "ratio_name": r_name,
                "ratio_value": r["value_formatted"],
                "outlier_reason": flag_reason,
            })

    if not outliers:
        return pd.DataFrame()

    return pd.DataFrame(outliers).drop_duplicates(subset=["ticker", "cal_year", "ratio_name"])


def audit_phase3_cross_correlation(
    anomalies_df: pd.DataFrame,
    ratios_df: pd.DataFrame,
) -> pd.DataFrame:
    """Cross-reference Phase 3's 17 distress outliers against Phase 4 anomaly scores."""
    outliers = extract_phase3_outliers(ratios_df)
    if outliers.empty:
        return pd.DataFrame()

    correlation_rows = []
    for (t, yr), group in outliers.groupby(["ticker", "cal_year"]):
        ratios_flagged = ", ".join(f"{r['ratio_name']} ({r['ratio_value']})" for _, r in group.iterrows())
        primary_reasons = "; ".join(group["outlier_reason"].unique())

        # Match with anomalies
        anom_sub = anomalies_df[(anomalies_df["ticker"] == t) & (anomalies_df["cal_year"] == yr)]

        z_row = anom_sub[anom_sub["anomaly_name"] == "adapted_altman_z_score"]
        m_row = anom_sub[anom_sub["anomaly_name"] == "adapted_beneish_m_score"]
        acc_row = anom_sub[anom_sub["anomaly_name"] == "accruals_ratio"]

        z_class = z_row["classification"].values[0] if not z_row.empty else "N/A"
        z_score = z_row["score_formatted"].values[0] if not z_row.empty else "N/A"
        m_class = m_row["classification"].values[0] if not m_row.empty else "N/A"
        m_score = m_row["score_formatted"].values[0] if not m_row.empty else "N/A"
        acc_class = acc_row["classification"].values[0] if not acc_row.empty else "N/A"
        acc_score = acc_row["score_formatted"].values[0] if not acc_row.empty else "N/A"

        # Determine correlation signal
        is_z_distress = z_class == "DISTRESS_ZONE"
        is_pre_ipo = "PRE_IPO" in z_class
        is_high_accruals = acc_class == "HIGH_ACCRUALS_RISK"
        is_m_flagged = m_class == "ELEVATED_MANIPULATION_RISK"

        if is_z_distress:
            signal = "CONFIRMED: Z-Score Distress Zone aligns with ratio distress"
        elif is_pre_ipo:
            signal = "PRE-IPO: Z-Score safely guarded; ratio reflects early-stage venture burn"
        elif is_high_accruals or is_m_flagged:
            signal = "CONFIRMED: Earnings-quality/accrual red-flags accompany ratio distortion"
        else:
            signal = f"MODERATE: Z-Score in {z_class} buffered by liquidity or equity base"

        correlation_rows.append({
            "ticker": t,
            "cal_year": yr,
            "phase3_flagged_ratios": ratios_flagged,
            "phase3_outlier_reason": primary_reasons,
            "adapted_z_score": z_score,
            "z_zone": z_class,
            "adapted_m_score": m_score,
            "m_class": m_class,
            "accruals_ratio": acc_score,
            "correlation_signal": signal,
        })

    return pd.DataFrame(correlation_rows).sort_values(["ticker", "cal_year"]).reset_index(drop=True)
