"""
anomaly/divergence.py — Revenue vs. Receivables Growth Divergence Engine.

Formula:
    Divergence = Receivables Growth YoY - Revenue Growth YoY

WHY this matters for credit & earnings quality:
  When a lender's loan receivables expand significantly faster than revenue,
  it often indicates loosening credit standards, aggressive loan-volume booking,
  or delayed recognition of non-accrual loans.

EXPLICIT EXEMPTION:
  For PGY and ENVA, receivables are off-balance-sheet (securitized ABS) or carried
  under ASC 825 Fair Value Option. Standard receivables growth is structurally
  inapplicable, and an explicit N/A string is output.
"""

import math
from typing import Optional, Any
import pandas as pd


def compute_divergence_for_company(ticker: str, cik: str, df_comp: pd.DataFrame) -> list[dict]:
    """Compute Revenue vs. Receivables Growth Divergence for a single company."""
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

        # Exemption for PGY and ENVA
        if ticker in ("PGY", "ENVA"):
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "growth_divergence",
                "score_value": float("nan"),
                "score_formatted": "N/A — securitized/fair-value receivables structure",
                "classification": "NOT_APPLICABLE",
                "explanation": "Receivables are off-balance-sheet or carried under ASC 825 Fair Value Option; revenue-receivables divergence is structurally inapplicable.",
                "rev_growth": float("nan"),
                "rec_growth": float("nan"),
            })
            continue

        if i == 0:
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "growth_divergence",
                "score_value": float("nan"),
                "score_formatted": "N/A — initial history period",
                "classification": "INSUFFICIENT_HISTORY",
                "explanation": "Requires prior-year baseline (t-1) to compute growth rates.",
                "rev_growth": float("nan"),
                "rec_growth": float("nan"),
            })
            continue

        prev = data[years[i - 1]]
        curr = data[yr]

        rev_t = curr.get("revenue")
        rev_prev = prev.get("revenue")
        rec_t = curr.get("receivables")
        rec_prev = prev.get("receivables")

        if (
            rev_t is None or math.isnan(rev_t)
            or rev_prev is None or math.isnan(rev_prev) or rev_prev <= 0
            or rec_t is None or math.isnan(rec_t)
            or rec_prev is None or math.isnan(rec_prev) or rec_prev <= 0
        ):
            results.append({
                "ticker": ticker,
                "cik": cik,
                "cal_year": yr,
                "fiscal_period_end": end_date,
                "anomaly_name": "growth_divergence",
                "score_value": float("nan"),
                "score_formatted": "N/A — missing revenue or receivables",
                "classification": "MISSING_DATA",
                "explanation": "Cannot compute divergence due to missing or non-positive revenue or receivables figures.",
                "rev_growth": float("nan"),
                "rec_growth": float("nan"),
            })
            continue

        rev_growth = (rev_t - rev_prev) / rev_prev
        rec_growth = (rec_t - rec_prev) / rec_prev
        divergence = rec_growth - rev_growth

        # Thresholds: > 20 percentage points divergence
        if divergence > 0.20:
            classification = "WARNING_RECEIVABLES_SURGE"
            desc = "WARNING: Receivables growth significantly outpaces revenue (> +20%)"
        elif divergence < -0.20:
            classification = "RAPID_TURNOVER_EXPANSION"
            desc = "TURNOVER EXPANSION: Revenue growth significantly outpaces receivables (> +20%)"
        else:
            classification = "NORMAL_ALIGNED"
            desc = "NORMAL: Revenue and receivables growth are reasonably aligned (within +/-20%)"

        rev_pct = rev_growth * 100
        rec_pct = rec_growth * 100
        div_pct = divergence * 100

        explanation = (
            f"Divergence = {div_pct:+.1f}% ({desc}). "
            f"Receivables grew {rec_pct:+.1f}% YoY (${rec_prev/1e6:.0f}M -> ${rec_t/1e6:.0f}M) "
            f"while Revenue grew {rev_pct:+.1f}% YoY (${rev_prev/1e6:.0f}M -> ${rev_t/1e6:.0f}M)."
        )

        results.append({
            "ticker": ticker,
            "cik": cik,
            "cal_year": yr,
            "fiscal_period_end": end_date,
            "anomaly_name": "growth_divergence",
            "score_value": divergence,
            "score_formatted": f"{div_pct:+.1f}%",
            "classification": classification,
            "explanation": explanation,
            "rev_growth": rev_growth,
            "rec_growth": rec_growth,
        })

    return results
