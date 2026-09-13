"""
ratios/ratio_engine.py — Comprehensive Financial Ratio Engine.

Computes 10 standardized ratios across 4 analytical categories:
  1. Profitability:
     - roe (Return on Equity): net_income / shareholders_equity
     - roa (Return on Assets): net_income / total_assets
     - net_margin: net_income / revenue
     - gross_margin: Explicit N/A ("N/A — no COGS concept for lenders")
  2. Leverage:
     - debt_to_equity: total_debt / shareholders_equity
     - interest_coverage: ebit / interest_expense
       (Computes synthetic EBIT: NetIncome + Tax + Interest for bank/lending filers)
  3. Liquidity:
     - current_ratio: Explicit N/A ("N/A — lenders don't classify current/non-current assets")
     - quick_ratio: Explicit N/A ("N/A — lenders don't classify current/non-current assets")
  4. Efficiency:
     - asset_turnover: revenue / total_assets
     - receivables_turnover: revenue / receivables
       (Explicit N/A for PGY and ENVA due to off-balance-sheet/FVO securitization)

Guardrails:
  - Zero-division safety: NEVER divide by zero silently. Outputs explicit reason string.
  - Distressed value preservation: Negative equity or distressed coverage are preserved,
    never clamped, and flagged in quality_note for downstream analysis.
  - Traceability: Ratios inherit the data-quality flags of their underlying line items
    (RESTATED, FALLBACK, SYNTHETIC_EBIT, etc.).
"""

import logging
import math
from typing import Optional, Any

import numpy as np
import pandas as pd

from ingestion.store import read_financials

logger = logging.getLogger(__name__)


def _format_val(val: float, mode: str) -> str:
    """Format numeric ratio for presentation."""
    if val is None or math.isnan(val) or math.isinf(val):
        return "N/A"
    if mode == "pct":
        return f"{val * 100:.2f}%"
    if mode == "mult":
        return f"{val:.2f}x"
    return f"{val:.4f}"


def _format_currency(val: Optional[float]) -> str:
    """Helper to format dollar amounts in quality notes."""
    if val is None or math.isnan(val):
        return "NaN"
    sign = "-" if val < 0 else ""
    abs_val = abs(val)
    if abs_val >= 1e9:
        return f"{sign}${abs_val / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"{sign}${abs_val / 1e6:.1f}M"
    if abs_val >= 1e3:
        return f"{sign}${abs_val / 1e3:.1f}K"
    return f"{sign}${abs_val:.0f}"


def _combine_quality_flags(*items: tuple[str, str, Optional[float]]) -> tuple[str, str]:
    """Combine input data-quality flags into a composite flag and human-readable note.

    Each item is (name, flag, value).
    """
    flags = [flag for _, flag, _ in items if flag]
    notes = [f"{name}: {_format_currency(val)} ({flag})" for name, flag, val in items if name]

    has_restated = any("RESTATED" in f for f in flags)
    has_fallback = any("FALLBACK" in f for f in flags)
    has_synthetic = any("SYNTHETIC" in f for f in flags)
    all_comparative = all("COMPARATIVE" in f for f in flags) if flags else False
    all_ok = all("OK" in f for f in flags) if flags else False

    composite_parts = []
    if has_restated:
        composite_parts.append("RESTATED")
    if has_fallback:
        composite_parts.append("FALLBACK")
    if has_synthetic:
        composite_parts.append("SYNTHETIC_EBIT")

    if not composite_parts:
        if all_comparative:
            composite_flag = "COMPARATIVE"
        elif all_ok:
            composite_flag = "OK"
        else:
            composite_flag = "OK"
    else:
        composite_flag = "|".join(composite_parts)

    note_str = " / ".join(notes)
    return composite_flag, note_str


def compute_ratios_for_company(
    ticker: str,
    cik: str,
    df_company: pd.DataFrame,
) -> pd.DataFrame:
    """Compute all 10 ratios for a single company across its available calendar years."""
    # Pivot company rows into a lookup structure: {cal_year: {line_item: (value, data_quality, fiscal_period_end)}}
    period_data: dict[int, dict[str, dict[str, Any]]] = {}

    for _, row in df_company.iterrows():
        yr = int(row["cal_year"])
        li = row["line_item"]
        if yr not in period_data:
            period_data[yr] = {}
        period_data[yr][li] = {
            "val": row["value"],
            "dq": row["data_quality"],
            "end": row.get("fiscal_period_end"),
        }

    ratio_rows: list[dict] = []

    for cal_year in sorted(period_data.keys()):
        items = period_data[cal_year]

        # Extract line items with defaults
        def get_item(name: str) -> tuple[Optional[float], str]:
            entry = items.get(name, {})
            val = entry.get("val")
            dq = entry.get("dq", "MISSING_TAG")
            if val is not None and (math.isnan(val) or math.isinf(val)):
                val = None
            return val, dq

        rev, rev_dq = get_item("revenue")
        ni, ni_dq = get_item("net_income")
        ta, ta_dq = get_item("total_assets")
        tl, tl_dq = get_item("total_liabilities")
        eq, eq_dq = get_item("shareholders_equity")
        rec, rec_dq = get_item("receivables")
        ocf, ocf_dq = get_item("operating_cash_flow")
        ie, ie_dq = get_item("interest_expense")
        debt, debt_dq = get_item("total_debt")
        ebit, ebit_dq = get_item("ebit")
        tax, tax_dq = get_item("income_tax_expense")

        # Period end date
        period_end = None
        for entry in items.values():
            if entry.get("end"):
                period_end = entry["end"]
                break

        # -------------------------------------------------------------------
        # 1. Profitability Ratios
        # -------------------------------------------------------------------

        # ROE: net_income / shareholders_equity
        if eq is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing equity", "MISSING_DATA",
                "Shareholders equity is missing."
            )
        elif eq == 0:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — zero equity", "ZERO_DENOMINATOR",
                "Shareholders equity is zero; division by zero guarded."
            )
        elif ni is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing net income", "MISSING_DATA",
                "Net income is missing."
            )
        else:
            r_val = ni / eq
            r_fmt = _format_val(r_val, "pct")
            r_dq, r_note = _combine_quality_flags(("net_income", ni_dq, ni), ("equity", eq_dq, eq))
            if eq < 0:
                r_dq = f"{r_dq}|DISTORTED_NEGATIVE_EQUITY" if r_dq != "OK" else "DISTORTED_NEGATIVE_EQUITY"
                r_note += " [NOTE: Negative equity distorts ROE directionality]"

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "profitability", "ratio_name": "roe",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

        # ROA: net_income / total_assets
        if ta is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing assets", "MISSING_DATA",
                "Total assets is missing."
            )
        elif ta <= 0:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — zero or negative assets", "ZERO_DENOMINATOR",
                "Total assets is <= 0; division guarded."
            )
        elif ni is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing net income", "MISSING_DATA",
                "Net income is missing."
            )
        else:
            r_val = ni / ta
            r_fmt = _format_val(r_val, "pct")
            r_dq, r_note = _combine_quality_flags(("net_income", ni_dq, ni), ("assets", ta_dq, ta))

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "profitability", "ratio_name": "roa",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

        # Net Margin: net_income / revenue
        if rev is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing revenue", "MISSING_DATA",
                "Revenue is missing."
            )
        elif rev <= 0:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — zero or negative revenue", "ZERO_DENOMINATOR",
                "Revenue is <= 0; division guarded."
            )
        elif ni is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing net income", "MISSING_DATA",
                "Net income is missing."
            )
        else:
            r_val = ni / rev
            r_fmt = _format_val(r_val, "pct")
            r_dq, r_note = _combine_quality_flags(("net_income", ni_dq, ni), ("revenue", rev_dq, rev))

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "profitability", "ratio_name": "net_margin",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

        # Gross Margin: Explicit N/A
        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "profitability", "ratio_name": "gross_margin",
            "value": float("nan"),
            "value_formatted": "N/A — no COGS concept for lenders",
            "data_quality": "NOT_APPLICABLE",
            "quality_note": "Consumer lenders do not report Cost of Goods Sold per METHODOLOGY.md.",
        })

        # -------------------------------------------------------------------
        # 2. Leverage Ratios
        # -------------------------------------------------------------------

        # Debt to Equity: total_debt / shareholders_equity
        if debt is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing debt data", "MISSING_DATA",
                "Total debt is missing."
            )
        elif eq is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing equity", "MISSING_DATA",
                "Shareholders equity is missing."
            )
        elif eq == 0:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — zero equity", "ZERO_DENOMINATOR",
                "Shareholders equity is zero; division by zero guarded."
            )
        else:
            r_val = debt / eq
            r_fmt = _format_val(r_val, "mult")
            r_dq, r_note = _combine_quality_flags(("total_debt", debt_dq, debt), ("equity", eq_dq, eq))
            if eq < 0:
                r_dq = f"{r_dq}|DISTORTED_NEGATIVE_EQUITY" if r_dq != "OK" else "DISTORTED_NEGATIVE_EQUITY"
                r_note += " [NOTE: Negative equity yields negative D/E ratio indicating balance-sheet distress]"

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "leverage", "ratio_name": "debt_to_equity",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

        # Interest Coverage: EBIT / interest_expense
        # For companies without direct OperatingIncomeLoss (SOFI, LC, OMF, OPRT), compute synthetic EBIT
        ebit_val = ebit
        ebit_flag = ebit_dq
        is_synthetic = False

        if ebit_val is None:
            if ni is not None and ie is not None:
                tax_val = tax if tax is not None else 0.0
                ebit_val = ni + tax_val + ie
                ebit_flag = "SYNTHETIC_EBIT"
                is_synthetic = True

        if ie is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing interest expense", "MISSING_DATA",
                "Interest expense is missing."
            )
        elif ie <= 0:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — zero interest expense", "ZERO_DENOMINATOR",
                "Interest expense is <= 0; coverage is undefined/infinite."
            )
        elif ebit_val is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing EBIT data", "MISSING_DATA",
                "Neither direct EBIT nor components for synthetic EBIT were available."
            )
        else:
            r_val = ebit_val / ie
            r_fmt = _format_val(r_val, "mult")
            r_dq, r_note = _combine_quality_flags(("ebit", ebit_flag, ebit_val), ("interest_expense", ie_dq, ie))
            if is_synthetic:
                r_note += f" [Synthetic EBIT: NI({_format_currency(ni)}) + Tax({_format_currency(tax)}) + Int({_format_currency(ie)})]"

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "leverage", "ratio_name": "interest_coverage",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

        # -------------------------------------------------------------------
        # 3. Liquidity Ratios (Explicit N/A per METHODOLOGY.md)
        # -------------------------------------------------------------------

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "liquidity", "ratio_name": "current_ratio",
            "value": float("nan"),
            "value_formatted": "N/A — lenders don't classify current/non-current assets",
            "data_quality": "NOT_APPLICABLE",
            "quality_note": "Consumer lenders do not report classified balance sheets per METHODOLOGY.md.",
        })

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "liquidity", "ratio_name": "quick_ratio",
            "value": float("nan"),
            "value_formatted": "N/A — lenders don't classify current/non-current assets",
            "data_quality": "NOT_APPLICABLE",
            "quality_note": "Consumer lenders do not report classified balance sheets per METHODOLOGY.md.",
        })

        # -------------------------------------------------------------------
        # 4. Efficiency Ratios
        # -------------------------------------------------------------------

        # Asset Turnover: revenue / total_assets
        if ta is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing assets", "MISSING_DATA",
                "Total assets is missing."
            )
        elif ta <= 0:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — zero or negative assets", "ZERO_DENOMINATOR",
                "Total assets is <= 0; division guarded."
            )
        elif rev is None:
            r_val, r_fmt, r_dq, r_note = (
                float("nan"), "N/A — missing revenue", "MISSING_DATA",
                "Revenue is missing."
            )
        else:
            r_val = rev / ta
            r_fmt = _format_val(r_val, "mult")
            r_dq, r_note = _combine_quality_flags(("revenue", rev_dq, rev), ("assets", ta_dq, ta))

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "efficiency", "ratio_name": "asset_turnover",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

        # Receivables Turnover: revenue / receivables
        # For PGY and ENVA: explicit N/A
        if ticker in ("PGY", "ENVA"):
            r_val = float("nan")
            r_fmt = "N/A — securitized/fair-value receivables structure"
            r_dq = "NOT_APPLICABLE"
            r_note = "Receivables are off-balance-sheet / carried under ASC 825 Fair Value Option; turnover is non-comparable."
        elif rec is None:
            r_val = float("nan")
            r_fmt = "N/A — missing receivables"
            r_dq = "MISSING_DATA"
            r_note = "Receivables line item is missing."
        elif rec <= 0:
            r_val = float("nan")
            r_fmt = "N/A — zero or negative receivables"
            r_dq = "ZERO_DENOMINATOR"
            r_note = "Receivables is <= 0; division guarded."
        elif rev is None:
            r_val = float("nan")
            r_fmt = "N/A — missing revenue"
            r_dq = "MISSING_DATA"
            r_note = "Revenue is missing."
        else:
            r_val = rev / rec
            r_fmt = _format_val(r_val, "mult")
            r_dq, r_note = _combine_quality_flags(("revenue", rev_dq, rev), ("receivables", rec_dq, rec))

        ratio_rows.append({
            "ticker": ticker, "cik": cik, "cal_year": cal_year, "fiscal_period_end": period_end,
            "ratio_category": "efficiency", "ratio_name": "receivables_turnover",
            "value": r_val, "value_formatted": r_fmt, "data_quality": r_dq, "quality_note": r_note,
        })

    return pd.DataFrame(ratio_rows)


def compute_all_ratios(df_financials: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Compute financial ratios for all companies in the normalized financials table."""
    if df_financials is None:
        df_financials = read_financials()

    if df_financials.empty:
        logger.error("Financials table is empty — cannot compute ratios.")
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []

    for ticker, group in df_financials.groupby("ticker"):
        cik = str(group["cik"].iloc[0])
        logger.info(f"Computing ratios for: {ticker} (CIK: {cik})")
        comp_df = compute_ratios_for_company(ticker=ticker, cik=cik, df_company=group)
        frames.append(comp_df)
        logger.info(f"[{ticker}] Computed {len(comp_df)} ratio rows across {comp_df['cal_year'].nunique()} years.")

    if not frames:
        return pd.DataFrame()

    all_ratios = pd.concat(frames, ignore_index=True)
    all_ratios = all_ratios.sort_values(["ticker", "cal_year", "ratio_category", "ratio_name"]).reset_index(drop=True)
    return all_ratios
