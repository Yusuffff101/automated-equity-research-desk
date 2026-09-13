"""
tests/test_ratios.py — Unit tests for the financial ratio engine.
"""

import math
import pandas as pd
import pytest

from ratios.ratio_engine import compute_ratios_for_company, compute_all_ratios


def test_gross_margin_domain_guardrail():
    """Lenders do not have COGS; gross margin must strictly return None and explicit explanation."""
    # Synthetic tidy financial dataframe for a lender
    data = [
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "revenue", "value": 1000.0, "data_quality": "OK"},
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "net_income", "value": 50.0, "data_quality": "OK"},
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "total_assets", "value": 2000.0, "data_quality": "OK"},
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "shareholders_equity", "value": 500.0, "data_quality": "OK"},
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "total_debt", "value": 1000.0, "data_quality": "OK"},
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "ebit", "value": 80.0, "data_quality": "OK"},
        {"ticker": "UPST", "cik": "0001647639", "cal_year": 2025, "line_item": "interest_expense", "value": 40.0, "data_quality": "OK"},
    ]
    df = pd.DataFrame(data)
    ratios_df = compute_all_ratios(df)

    # Check gross margin
    gm_row = ratios_df[ratios_df["ratio_name"] == "gross_margin"].iloc[0]
    assert pd.isna(gm_row["value"])
    assert gm_row["data_quality"] == "NOT_APPLICABLE"
    assert "Cost of Goods Sold" in gm_row["quality_note"]

    # Check ROE
    roe_row = ratios_df[ratios_df["ratio_name"] == "roe"].iloc[0]
    assert math.isclose(roe_row["value"], 0.10, rel_tol=1e-4)

    # Check Interest Coverage
    cov_row = ratios_df[ratios_df["ratio_name"] == "interest_coverage"].iloc[0]
    assert math.isclose(cov_row["value"], 2.0, rel_tol=1e-4)
