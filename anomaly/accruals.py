"""
anomaly/accruals.py — Balance-Sheet Accruals Ratio Engine.

Formula:
    Accruals Ratio = (Net Income - Operating Cash Flow) / Total Assets

WHY this matters for earnings quality:
  High positive accruals indicate that reported GAAP earnings are not being
  converted into cash from operations. In consumer lending, this frequently
  signals uncollected interest accruals, delayed charge-offs/provisions, or
  non-cash valuation gains on loan portfolios.
"""

import math
from typing import Optional, Any
import pandas as pd


def compute_accruals_for_company(ticker: str, cik: str, df_comp: pd.DataFrame) -> list[dict]:
    """Compute Balance-Sheet Accruals Ratio for a single company across calendar years."""
    data: dict[int, dict[str, Any]] = {}
    for _, row in df_comp.iterrows():
        yr = int(row["cal_year"])
        li = row["line_item"]
        if yr not in data:
            data[yr] = {}
        data[yr][li] = row["value"]
        if "fiscal_period_end" in row and row["fiscal_period_end"]:
            data[yr]["_end"] = row["fiscal_period_end"]

    results: list[dict] = []

    for yr in sorted(data.keys()):
        curr = data[yr]
        end_date = curr.get("_end")

        ni = curr.get("net_income")
        cfo = curr.get("operating_cash_flow")
        ta = curr.get("total_assets")

        if (
            ni is None or math.isnan(ni)
            or cfo is None or math.isnan(cfo)
            or ta is None or math.isnan(ta) or ta <= 0
        ):
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "accruals_ratio",
                "score_value": float("nan"),
                "score_formatted": "N/A — missing NI, CFO, or Assets",
                "classification": "MISSING_DATA",
                "explanation": "Cannot compute Accruals Ratio due to missing Net Income, Operating Cash Flow, or Assets.",
            })
            continue

        accruals_dollars = ni - cfo
        accruals_ratio = accruals_dollars / ta

        # Classification
        if accruals_ratio > 0.10:
            classification = "HIGH_ACCRUALS_RISK"
            desc = "HIGH RISK: Earnings heavily exceed cash flow (> 10% of assets)"
        elif accruals_ratio > 0.05:
            classification = "ELEVATED_ACCRUALS"
            desc = "ELEVATED: Modest cash lag (5%–10% of assets)"
        elif accruals_ratio < -0.10:
            classification = "STRONG_CASH_CONVERSION"
            desc = "HIGH QUALITY: Cash flow significantly exceeds net income"
        else:
            classification = "NORMAL_ACCRUALS"
            desc = "NORMAL: Accruals align closely with cash flow (<= 5% of assets)"

        ni_desc = f"${ni / 1e6:+.1f}M"
        cfo_desc = f"${cfo / 1e6:+.1f}M"
        diff_desc = f"${accruals_dollars / 1e6:+.1f}M"
        ta_desc = f"${ta / 1e9:.2f}B" if ta >= 1e9 else f"${ta / 1e6:.0f}M"

        explanation = (
            f"Accruals Ratio = {accruals_ratio:+.3f} ({desc}). "
            f"Net Income ({ni_desc}) minus CFO ({cfo_desc}) = {diff_desc} net accruals on {ta_desc} total assets."
        )

        results.append({
            "ticker": ticker,
            "cik": cik,
            "cal_year": yr,
            "fiscal_period_end": end_date,
            "anomaly_name": "accruals_ratio",
            "score_value": accruals_ratio,
            "score_formatted": f"{accruals_ratio:+.3f}",
            "classification": classification,
            "explanation": explanation,
        })

    return results
