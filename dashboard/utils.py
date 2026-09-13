"""
dashboard/utils.py — Styling, formatting, outlier scaling, and metric metadata.
"""

import math
from typing import Optional, Any
import numpy as np
import pandas as pd

# Curated institutional color palette for the 9 public peers
PEER_COLORS = {
    "AFRM": "#2563eb",  # Royal Blue
    "SEZL": "#06b6d4",  # Cyan / Turquoise
    "UPST": "#8b5cf6",  # Violet
    "SOFI": "#3b82f6",  # Cobalt
    "LC":   "#10b981",  # Emerald
    "PGY":  "#f97316",  # Coral / Orange
    "OPRT": "#e11d48",  # Rose Red
    "OMF":  "#64748b",  # Steel Slate
    "ENVA": "#d97706",  # Amber Ochre
}

# Risk status badge colors
STATUS_COLORS = {
    "DISTRESS_ZONE": "#ef4444",
    "ELEVATED_MANIPULATION_RISK": "#ef4444",
    "HIGH_ACCRUALS_RISK": "#ef4444",
    "HIGH_DIVERGENCE_RISK": "#ef4444",
    "GREY_ZONE": "#f59e0b",
    "MODERATE_DIVERGENCE": "#f59e0b",
    "SAFE_ZONE": "#10b981",
    "LOW_MANIPULATION_RISK": "#10b981",
    "STRONG_CASH_CONVERSION": "#10b981",
    "NORMAL_ACCRUALS": "#3b82f6",
    "PRE_IPO_UNAVAILABLE": "#64748b",
    "NOT_APPLICABLE": "#8b5cf6",
    "MISSING_DATA": "#94a3b8",
    "INSUFFICIENT_HISTORY": "#94a3b8",
}

# Comprehensive dictionary of all metrics, formulas, adaptation notes, and tooltips
METRIC_METADATA = {
    # Ratios
    "roe": {
        "label": "Return on Equity (ROE)",
        "adaptation_label": "Standard Formula (Distorted by Negative Equity)",
        "category": "Profitability",
        "format": "percent",
        "tooltip": "Net Income / Shareholders' Equity. Lenders with accumulated deficits have negative equity, causing severe sign inversion distortions (e.g. SEZL FY2022 -430%).",
        "clip_bounds": (-1.0, 1.0),  # -100% to +100%
    },
    "roa": {
        "label": "Return on Assets (ROA)",
        "adaptation_label": "Standard Formula",
        "category": "Profitability",
        "format": "percent",
        "tooltip": "Net Income / Total Assets. Key profitability benchmark across financial institutions, unaffected by leverage distortions.",
        "clip_bounds": (-0.20, 0.20),
    },
    "net_margin": {
        "label": "Net Profit Margin",
        "adaptation_label": "Standard Formula",
        "category": "Profitability",
        "format": "percent",
        "tooltip": "Net Income / Total Revenue. Measures bottom-line earnings conversion per dollar of lending fees and interest income.",
        "clip_bounds": (-1.0, 0.50),
    },
    "debt_to_equity": {
        "label": "Debt-to-Equity",
        "adaptation_label": "Includes Warehouse & Securitization Debt",
        "category": "Leverage",
        "format": "multiplier",
        "tooltip": "Total Debt / Shareholders' Equity. Captures corporate borrowings plus warehouse facilities and ABS debt.",
        "clip_bounds": (0.0, 25.0),
    },
    "interest_coverage": {
        "label": "Interest Coverage",
        "adaptation_label": "Synthetic EBIT for Pure Lenders",
        "category": "Leverage",
        "format": "multiplier",
        "tooltip": "EBIT / Interest Expense. For filers lacking direct operating income (SOFI, LC, OMF, OPRT), Synthetic EBIT = Net Income + Tax + Interest Expense.",
        "clip_bounds": (-10.0, 15.0),
    },
    "asset_turnover": {
        "label": "Asset Turnover",
        "adaptation_label": "Standard Formula",
        "category": "Efficiency",
        "format": "multiplier",
        "tooltip": "Revenue / Total Assets. Measures velocity of revenue generation relative to the lending balance sheet.",
        "clip_bounds": (0.0, 1.5),
    },
    "receivables_turnover": {
        "label": "Receivables Turnover",
        "adaptation_label": "Exempt for PGY & ENVA (Securitized/FVO)",
        "category": "Efficiency",
        "format": "multiplier",
        "tooltip": "Revenue / Receivables. Measures customer loan repayment speed. Structurally N/A for PGY and ENVA due to off-balance-sheet or ASC 825 FVO accounting.",
        "clip_bounds": (0.0, 10.0),
    },
    # Anomalies
    "adapted_altman_z_score": {
        "label": "Altman Z-Score",
        "adaptation_label": "Adapted Z-Score (Cash/TA substitution)",
        "category": "Distress / Solvency",
        "format": "decimal_2",
        "tooltip": "Classical Altman Z adapted for lenders: Cash/TA substitutes for Working Capital/TA (unclassified balance sheet). MVE/TL from year-end market data. Z < 1.81 = Distress Zone; 1.81-2.99 = Grey Zone; > 2.99 = Safe Zone.",
        "clip_bounds": (-2.0, 12.0),
    },
    "adapted_beneish_m_score": {
        "label": "Beneish M-Score",
        "adaptation_label": "Adapted M-Score (ex-GMI, financial institution adjustment)",
        "category": "Earnings Quality / Manipulation",
        "format": "decimal_2",
        "tooltip": "Forensic accounting model adapted for lenders: Gross Margin Index (GMI) is excluded (no COGS for lenders). DSRI is neutralized to 1.0 for PGY/ENVA. Scores > -1.78 indicate elevated manipulation/aggressive accrual risk relative to peers.",
        "clip_bounds": (-5.0, 3.0),
    },
    "accruals_ratio": {
        "label": "Accruals Ratio",
        "adaptation_label": "Balance-Sheet Accruals: (NI - CFO) / TA",
        "category": "Earnings Quality",
        "format": "decimal_3",
        "tooltip": "(Net Income − Operating Cash Flow) / Total Assets. High positive values (> +0.10) signal uncollected interest, delayed provisioning, or non-cash valuation gains. Negative values indicate cash conversion exceeding GAAP net income.",
        "clip_bounds": (-0.50, 0.50),
    },
    "growth_divergence": {
        "label": "Growth Divergence",
        "adaptation_label": "Receivables YoY - Revenue YoY (N/A for PGY/ENVA)",
        "category": "Credit Growth",
        "format": "percent",
        "tooltip": "YoY Receivables Growth minus YoY Revenue Growth. Spreads > +15% signal aggressive loan volume booking or delayed non-accrual reclassifications. Explicitly N/A for PGY and ENVA due to securitization/fair-value structures.",
        "clip_bounds": (-1.0, 2.0),
    },
}


def format_metric_value(val: Any, format_type: str) -> str:
    """Format numeric values cleanly according to metric type."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return "N/A"

    try:
        f_val = float(val)
        if format_type == "percent":
            return f"{f_val * 100:+.1f}%" if abs(f_val) < 100 else f"{f_val * 100:+.0f}%"
        elif format_type == "multiplier":
            return f"{f_val:.2f}x"
        elif format_type == "decimal_2":
            return f"{f_val:.2f}"
        elif format_type == "decimal_3":
            return f"{f_val:+.3f}"
        elif format_type == "currency_m":
            return f"${f_val / 1e6:,.1f}M"
        elif format_type == "currency_b":
            return f"${f_val / 1e9:,.2f}B"
        return f"{f_val:.2f}"
    except (ValueError, TypeError):
        return str(val)


def prepare_chart_series(
    df: pd.DataFrame,
    metric_key: str,
    clip_outliers: bool = True,
) -> pd.DataFrame:
    """
    Transform and augment data series for Plotly charting:
      1. Outlier capping with custom hover metadata
      2. Explicit N/A annotations for PRE_IPO, MISSING_DATA, NOT_APPLICABLE
    """
    plot_df = df.copy()
    meta = METRIC_METADATA.get(metric_key, {})
    bounds = meta.get("clip_bounds")
    fmt = meta.get("format", "decimal_2")

    # Value columns
    val_col = "value" if "value" in plot_df.columns else "score_value"
    formatted_col = "value_formatted" if "value_formatted" in plot_df.columns else "score_formatted"

    plot_vals = []
    is_clipped_list = []
    hover_notes = []
    data_states = []

    for _, row in plot_df.iterrows():
        raw_val = row.get(val_col)
        raw_fmt = row.get(formatted_col, "")
        dq = row.get("data_quality", row.get("classification", "OK"))

        # Check explicit N/A states
        is_pre_ipo = "PRE_IPO" in str(dq) or "Pre-IPO" in str(raw_fmt)
        is_not_applicable = "NOT_APPLICABLE" in str(dq) or "securitized" in str(raw_fmt)
        is_missing = "MISSING" in str(dq) or raw_val is None or (isinstance(raw_val, float) and math.isnan(raw_val))

        if is_pre_ipo:
            data_states.append("PRE_IPO")
            plot_vals.append(None)
            is_clipped_list.append(False)
            hover_notes.append("N/A — Pre-IPO (MVE unavailable, company not publicly traded)")
        elif is_not_applicable:
            data_states.append("NOT_APPLICABLE")
            plot_vals.append(None)
            is_clipped_list.append(False)
            hover_notes.append("N/A — Securitized / ASC 825 Fair Value Structure")
        elif is_missing:
            data_states.append("MISSING_DATA")
            plot_vals.append(None)
            is_clipped_list.append(False)
            hover_notes.append(f"N/A — {dq} (Pending Filing or Missing Tag)")
        else:
            val_float = float(raw_val)
            data_states.append("VALID")

            # Outlier clipping
            if clip_outliers and bounds is not None:
                lower, upper = bounds
                if val_float < lower:
                    plot_vals.append(lower)
                    is_clipped_list.append(True)
                    hover_notes.append(f"True Value: {format_metric_value(val_float, fmt)} [CLIPPED ON AXIS FOR READABILITY]")
                elif val_float > upper:
                    plot_vals.append(upper)
                    is_clipped_list.append(True)
                    hover_notes.append(f"True Value: {format_metric_value(val_float, fmt)} [CLIPPED ON AXIS FOR READABILITY]")
                else:
                    plot_vals.append(val_float)
                    is_clipped_list.append(False)
                    hover_notes.append(f"Value: {format_metric_value(val_float, fmt)}")
            else:
                plot_vals.append(val_float)
                is_clipped_list.append(False)
                hover_notes.append(f"Value: {format_metric_value(val_float, fmt)}")

    plot_df["plot_value"] = plot_vals
    plot_df["is_clipped"] = is_clipped_list
    plot_df["hover_note"] = hover_notes
    plot_df["data_state"] = data_states

    return plot_df
