"""
anomaly/altman.py — Adapted Altman Z-Score for Financial Institutions.

WHY standard Altman Z fails for lenders:
  1. The X1 = Working Capital / Total Assets term requires classified balance
     sheets (Current Assets - Current Liabilities). Banks and consumer lenders
     do not classify loans into current vs. non-current buckets.
  2. The X4 = Market Value of Equity / Total Liabilities term requires market
     capitalization as of each fiscal year-end date.

ADAPTATION METHODOLOGY:
  1. Substitute Cash & Cash Equivalents / Total Assets (Cash/TA) for WC/TA:
     - Cash & Equivalents is universally available across all 9 filers.
     - Cash is the truest liquid buffer to meet short-term commitments.
     - Substituting Cash makes the liquidity score conservative (Cash <= WC).
  2. Use Synthetic EBIT (NetIncome + Tax + Interest) for filers lacking direct
     OperatingIncomeLoss (SOFI, LC, OMF, OPRT), consistent with Phase 3.
  3. Pre-IPO Graceful Handling: For pre-IPO years (e.g. SEZL 2021-2022, AFRM 2020),
     MVE is unavailable. We output "N/A — Pre-IPO (MVE unavailable)", never
     fabricating private valuation or assuming zero.
  4. Formula:
     Z_adapted = 1.2*(Cash/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MVE/TL) + 0.999*(Sales/TA)
  5. Zones:
     - Distress Zone: Z < 1.81
     - Grey Zone:     1.81 <= Z <= 2.99
     - Safe Zone:       Z > 2.99
"""

import json
import logging
import math
from pathlib import Path
from typing import Optional, Any
import pandas as pd

from config import RAW_DIR
from ingestion.xbrl_normalizer import _extract_tag_records, _filter_annual_filings

logger = logging.getLogger(__name__)


def _get_cash_for_company(ticker: str) -> dict[str, float]:
    """Extract annual Cash and Cash Equivalents from raw EDGAR JSON."""
    raw_path = RAW_DIR / f"{ticker}.json"
    if not raw_path.exists():
        return {}

    try:
        with raw_path.open("r", encoding="utf-8") as f:
            facts = json.load(f)

        # Try standard cash tags
        for tag in ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalentsPeriodIncreaseDecrease"]:
            recs = _extract_tag_records(facts, tag)
            df_cash = _filter_annual_filings(recs)
            if not df_cash.empty:
                return {
                    row["end_date"].date().isoformat(): float(row["val"])
                    for _, row in df_cash.iterrows()
                }
    except Exception as e:
        logger.warning(f"[{ticker}] Failed to extract cash from raw JSON: {e}")

    return {}


def compute_adapted_altman_for_company(
    ticker: str,
    cik: str,
    df_comp: pd.DataFrame,
    df_mkt: pd.DataFrame,
) -> list[dict]:
    """Compute Adapted Altman Z-Score for a single company across its calendar years."""
    # Organize financial data into {cal_year: {line_item: value}}
    fin_data: dict[int, dict[str, Any]] = {}
    for _, row in df_comp.iterrows():
        yr = int(row["cal_year"])
        li = row["line_item"]
        if yr not in fin_data:
            fin_data[yr] = {}
        fin_data[yr][li] = row["value"]
        if "fiscal_period_end" in row and row["fiscal_period_end"]:
            fin_data[yr]["_end"] = row["fiscal_period_end"]

    # Market data lookup: {cal_year: (market_cap, is_pre_ipo, data_quality)}
    mkt_lookup: dict[int, dict[str, Any]] = {}
    if not df_mkt.empty:
        comp_mkt = df_mkt[df_mkt["ticker"] == ticker]
        for _, m_row in comp_mkt.iterrows():
            m_yr = int(m_row["cal_year"])
            mkt_lookup[m_yr] = {
                "mcap": m_row["market_cap"],
                "is_pre_ipo": m_row["is_pre_ipo"],
                "dq": m_row["data_quality"],
            }

    cash_by_end = _get_cash_for_company(ticker)
    results: list[dict] = []

    for yr in sorted(fin_data.keys()):
        curr = fin_data[yr]
        end_date = curr.get("_end")

        ta = curr.get("total_assets")
        tl = curr.get("total_liabilities")
        re = curr.get("retained_earnings")
        rev = curr.get("revenue")
        ni = curr.get("net_income")
        ie = curr.get("interest_expense")
        tax = curr.get("income_tax_expense")
        ebit_direct = curr.get("ebit")

        # 1. Cash (for X1 = Cash / TA)
        cash_val = cash_by_end.get(end_date, 0.0) if end_date else 0.0

        # 2. EBIT (X3): use direct if available, else synthetic (NI + Tax + Interest)
        ebit_val = ebit_direct
        is_synthetic_ebit = False
        if ebit_val is None or math.isnan(ebit_val):
            if ni is not None and not math.isnan(ni):
                t_val = tax if (tax is not None and not math.isnan(tax)) else 0.0
                i_val = ie if (ie is not None and not math.isnan(ie)) else 0.0
                ebit_val = ni + t_val + i_val
                is_synthetic_ebit = True

        # Missing fundamentals guardrail (checked first so pending future periods don't falsely claim pre-IPO)
        if (
            ta is None or math.isnan(ta) or ta <= 0
            or tl is None or math.isnan(tl) or tl <= 0
            or re is None or math.isnan(re)
            or rev is None or math.isnan(rev)
            or ebit_val is None or math.isnan(ebit_val)
        ):
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "adapted_altman_z_score",
                "score_value": float("nan"),
                "score_formatted": "N/A — missing fundamental components",
                "classification": "MISSING_DATA",
                "explanation": "Cannot compute Altman Z-Score due to missing fundamental line items (e.g. pending 10-K filing or unpopulated balance sheet tags).",
                "x1_cash_ta": float("nan"),
                "x2_re_ta": float("nan"),
                "x3_ebit_ta": float("nan"),
                "x4_mve_tl": float("nan"),
                "x5_sales_ta": float("nan"),
            })
            continue

        # 3. Market Cap (for X4 = MVE / TL)
        mkt_entry = mkt_lookup.get(yr, {})
        mcap = mkt_entry.get("mcap")
        is_pre_ipo = mkt_entry.get("is_pre_ipo", 0)

        # Pre-IPO Guardrail: do NOT fabricate private valuation
        if is_pre_ipo:
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "adapted_altman_z_score",
                "score_value": float("nan"),
                "score_formatted": "N/A — Pre-IPO (MVE unavailable)",
                "classification": "PRE_IPO_UNAVAILABLE",
                "explanation": "Company was not publicly traded as of this period-end; market capitalization is unavailable.",
                "x1_cash_ta": float("nan"),
                "x2_re_ta": float("nan"),
                "x3_ebit_ta": float("nan"),
                "x4_mve_tl": float("nan"),
                "x5_sales_ta": float("nan"),
            })
            continue

        if mcap is None or math.isnan(mcap):
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "adapted_altman_z_score",
                "score_value": float("nan"),
                "score_formatted": "N/A — market data unavailable",
                "classification": "MISSING_DATA",
                "explanation": "Market capitalization data unavailable as of fiscal year-end.",
                "x1_cash_ta": float("nan"),
                "x2_re_ta": float("nan"),
                "x3_ebit_ta": float("nan"),
                "x4_mve_tl": float("nan"),
                "x5_sales_ta": float("nan"),
            })
            continue


        # Component calculations
        x1 = cash_val / ta
        x2 = re / ta
        x3 = ebit_val / ta
        x4 = mcap / tl
        x5 = rev / ta

        z_score = (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + (0.999 * x5)

        # Classification
        if z_score < 1.81:
            zone = "DISTRESS_ZONE"
            zone_desc = "DISTRESS (< 1.81)"
        elif z_score <= 2.99:
            zone = "GREY_ZONE"
            zone_desc = "GREY ZONE (1.81–2.99)"
        else:
            zone = "SAFE_ZONE"
            zone_desc = "SAFE ZONE (> 2.99)"

        # Explanation string citing exact drivers
        re_sign = "negative (accumulated deficit)" if re < 0 else "positive"
        re_desc = f"{re / 1e6:+.0f}M"
        mcap_desc = f"${mcap / 1e9:.2f}B" if mcap >= 1e9 else f"${mcap / 1e6:.0f}M"
        tl_desc = f"${tl / 1e9:.2f}B" if tl >= 1e9 else f"${tl / 1e6:.0f}M"
        cash_desc = f"${cash_val / 1e6:.0f}M"

        explanation_parts = [
            f"Adapted Z-Score = {z_score:.2f} ({zone_desc}).",
            f"Drivers: Cash/TA = {x1:.2f} (Cash: {cash_desc}),",
            f"RE/TA = {x2:+.2f} ({re_sign} RE: {re_desc}),",
            f"EBIT/TA = {x3:+.2f}{' (Synthetic EBIT)' if is_synthetic_ebit else ''},",
            f"MVE/TL = {x4:.2f}x (MVE: {mcap_desc} / Liabilities: {tl_desc}),",
            f"Sales/TA = {x5:.2f}x.",
            "Cash/TA substituted for WC/TA per financial institution adaptation.",
        ]
        explanation = " ".join(explanation_parts)

        results.append({
            "ticker": ticker,
            "cik": cik,
            "cal_year": yr,
            "fiscal_period_end": end_date,
            "anomaly_name": "adapted_altman_z_score",
            "score_value": z_score,
            "score_formatted": f"{z_score:.2f}",
            "classification": zone,
            "explanation": explanation,
            "x1_cash_ta": x1,
            "x2_re_ta": x2,
            "x3_ebit_ta": x3,
            "x4_mve_tl": x4,
            "x5_sales_ta": x5,
        })

    return results
