"""
anomaly/beneish.py — Adapted Beneish M-Score for Financial Institutions (ex-GMI).

WHY standard Beneish fails for lenders:
  Beneish's Gross Margin Index (GMI) requires Gross Margin = (Rev - COGS) / Rev.
  As established in Phase 3, consumer lenders have no Cost of Goods Sold concept;
  revenues are derived from interest margins, gain-on-sale, and origination/servicing fees.

ADAPTATION METHODOLOGY:
  1. Exclude GMI (+0.528 * GMI dropped).
  2. Unobserved manufacturing-specific indexes (AQI, DEPI, SGAI) default to neutral 1.0.
  3. Base formula:
     M_adapted = -4.493 + 0.920*DSRI + 0.892*SGI + 4.037*TATA + 0.0327*LVGI
  4. Receivables Exception: For PGY and ENVA, receivables are off-balance-sheet
     or carried under ASC 825 Fair Value Option. DSRI is neutralized to 1.0 with
     an explicit footnote string.
  5. Directional Interpretation: The original -1.78 cutoff was calibrated with GMI.
     The adapted score is directional/comparative, surfacing aggressive accrual
     and receivables expansion relative to conservative peers.
"""

import math
from typing import Optional, Any
import pandas as pd


def compute_adapted_beneish_for_company(ticker: str, cik: str, df_comp: pd.DataFrame) -> list[dict]:
    """Compute Adapted Beneish M-Score for a single company across its calendar years."""
    # Organize into {year: {line_item: value}}
    data: dict[int, dict[str, Any]] = {}
    for _, row in df_comp.iterrows():
        yr = int(row["cal_year"])
        li = row["line_item"]
        if yr not in data:
            data[yr] = {}
        data[yr][li] = row["value"]
        if "fiscal_period_end" in row and row["fiscal_period_end"]:
            data[yr]["_end"] = row["fiscal_period_end"]

    years = sorted(data.keys())
    results: list[dict] = []

    for i, yr in enumerate(years):
        end_date = data[yr].get("_end")
        curr = data[yr]

        # Year 0 of time series has no prior-year comparison
        if i == 0:
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "adapted_beneish_m_score",
                "score_value": float("nan"),
                "score_formatted": "N/A — initial history period",
                "classification": "INSUFFICIENT_HISTORY",
                "explanation": "Beneish M-Score requires a prior-year baseline (t-1) to compute growth indexes.",
                "dsri": float("nan"),
                "sgi": float("nan"),
                "lvgi": float("nan"),
                "tata": float("nan"),
            })
            continue

        prev = data[years[i - 1]]

        rev_t = curr.get("revenue")
        rev_prev = prev.get("revenue")
        rec_t = curr.get("receivables")
        rec_prev = prev.get("receivables")
        ta_t = curr.get("total_assets")
        ta_prev = prev.get("total_assets")
        tl_t = curr.get("total_liabilities")
        tl_prev = prev.get("total_liabilities")
        ni_t = curr.get("net_income")
        cfo_t = curr.get("operating_cash_flow")

        # Guard: Check required fundamentals
        missing_vars = []
        if rev_t is None or math.isnan(rev_t) or rev_prev is None or math.isnan(rev_prev):
            missing_vars.append("revenue")
        if ta_t is None or math.isnan(ta_t) or ta_prev is None or math.isnan(ta_prev):
            missing_vars.append("total_assets")
        if tl_t is None or math.isnan(tl_t) or tl_prev is None or math.isnan(tl_prev):
            missing_vars.append("total_liabilities")
        if ni_t is None or math.isnan(ni_t):
            missing_vars.append("net_income")
        if cfo_t is None or math.isnan(cfo_t):
            missing_vars.append("operating_cash_flow")

        if missing_vars:
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "adapted_beneish_m_score",
                "score_value": float("nan"),
                "score_formatted": f"N/A — missing {', '.join(missing_vars)}",
                "classification": "MISSING_DATA",
                "explanation": f"Cannot compute Beneish M-Score due to missing historical inputs: {', '.join(missing_vars)}.",
                "dsri": float("nan"),
                "sgi": float("nan"),
                "lvgi": float("nan"),
                "tata": float("nan"),
            })
            continue

        # 1. SGI: Sales Growth Index
        if rev_prev <= 0:
            sgi = 1.0
        else:
            sgi = rev_t / rev_prev

        # 2. LVGI: Leverage Index (TL/TA)_t / (TL/TA)_{t-1}
        lev_t = tl_t / ta_t if ta_t > 0 else 1.0
        lev_prev = tl_prev / ta_prev if ta_prev > 0 else 1.0
        lvgi = lev_t / lev_prev if lev_prev > 0 else 1.0

        # 3. TATA: Total Accruals to Total Assets (NI - CFO) / TA
        tata = (ni_t - cfo_t) / ta_t if ta_t > 0 else 0.0

        # 4. DSRI: Days Sales in Receivables Index
        dsri_note = ""
        if ticker in ("PGY", "ENVA"):
            dsri = 1.0
            dsri_note = " (DSRI neutralized to 1.0 due to off-balance-sheet/FVO receivables)"
        elif rec_t is None or rec_prev is None or math.isnan(rec_t) or math.isnan(rec_prev) or rec_prev <= 0 or rev_prev <= 0 or rev_t <= 0:
            dsri = 1.0
            dsri_note = " (DSRI neutralized to 1.0 due to missing receivables baseline)"
        else:
            ratio_t = rec_t / rev_t
            ratio_prev = rec_prev / rev_prev
            dsri = ratio_t / ratio_prev if ratio_prev > 0 else 1.0

        # Compute Adapted M-Score
        m_score = -4.493 + (0.920 * dsri) + (0.892 * sgi) + (4.037 * tata) + (0.0327 * lvgi)

        # Classification
        # Directional threshold: -1.78
        is_elevated = m_score > -1.78
        classification = "ELEVATED_MANIPULATION_RISK" if is_elevated else "LOW_MANIPULATION_RISK"

        # Explanation string referencing actual numbers
        accruals_m = (ni_t - cfo_t) / 1e6
        rev_growth_pct = (sgi - 1.0) * 100

        explanation_parts = [
            f"Adapted M-Score (ex-GMI, financial institution adjustment) = {m_score:.2f} ({'ELEVATED RISK: > -1.78' if is_elevated else 'LOW RISK: <= -1.78'}).",
            f"Drivers: SGI = {sgi:.2f} ({rev_growth_pct:+.1f}% YoY revenue growth),",
            f"TATA = {tata:+.3f} (net accruals of ${accruals_m:+.1f}M vs assets),",
            f"DSRI = {dsri:.2f}{dsri_note},",
            f"LVGI = {lvgi:.2f}.",
            "Gross Margin Index (GMI) dropped per financial institution adjustment.",
        ]
        explanation = " ".join(explanation_parts)


        results.append({
            "ticker": ticker,
            "cik": cik,
            "cal_year": yr,
            "fiscal_period_end": end_date,
            "anomaly_name": "adapted_beneish_m_score",
            "score_value": m_score,
            "score_formatted": f"{m_score:.2f}",
            "classification": classification,
            "explanation": explanation,
            "dsri": dsri,
            "sgi": sgi,
            "lvgi": lvgi,
            "tata": tata,
        })

    return results
