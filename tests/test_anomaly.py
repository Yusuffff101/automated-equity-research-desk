"""
tests/test_anomaly.py — Unit and integration tests for Anomaly & Red-Flag Module (Phase 4).
"""

import math
import sqlite3
import unittest
import pandas as pd

from config import SQLITE_PATH, ANOMALIES_CSV_PATH, COMPANIES
from anomaly.beneish import compute_adapted_beneish_for_company
from anomaly.altman import compute_adapted_altman_for_company
from anomaly.accruals import compute_accruals_for_company
from anomaly.divergence import compute_divergence_for_company
from anomaly.detector import compute_all_anomalies, audit_phase3_cross_correlation
from anomaly.store import read_anomalies
from ratios.store import read_ratios


class TestAnomalyModule(unittest.TestCase):

    def test_adapted_beneish_ex_gmi_and_neutralization(self):
        """Test that Adapted Beneish drops GMI and neutralizes DSRI for PGY/ENVA."""
        mock_data_pgy = pd.DataFrame([
            {"cal_year": 2022, "line_item": "revenue", "value": 500.0, "fiscal_period_end": "2022-12-31"},
            {"cal_year": 2022, "line_item": "receivables", "value": 50.0, "fiscal_period_end": "2022-12-31"},
            {"cal_year": 2022, "line_item": "total_assets", "value": 1000.0, "fiscal_period_end": "2022-12-31"},
            {"cal_year": 2022, "line_item": "total_liabilities", "value": 400.0, "fiscal_period_end": "2022-12-31"},
            {"cal_year": 2022, "line_item": "total_debt", "value": 300.0, "fiscal_period_end": "2022-12-31"},
            {"cal_year": 2022, "line_item": "net_income", "value": 20.0, "fiscal_period_end": "2022-12-31"},
            {"cal_year": 2022, "line_item": "operating_cash_flow", "value": 30.0, "fiscal_period_end": "2022-12-31"},

            {"cal_year": 2023, "line_item": "revenue", "value": 600.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "receivables", "value": 80.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "total_assets", "value": 1200.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "total_liabilities", "value": 500.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "total_debt", "value": 350.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "net_income", "value": 25.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "operating_cash_flow", "value": 40.0, "fiscal_period_end": "2023-12-31"},

        ])

        results = compute_adapted_beneish_for_company("PGY", "0001857140", mock_data_pgy)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["classification"], "INSUFFICIENT_HISTORY")

        # 2023: DSRI should be neutralized to 1.0 for PGY
        row_2023 = results[1]
        self.assertEqual(row_2023["cal_year"], 2023)
        self.assertEqual(row_2023["dsri"], 1.0)
        self.assertIn("neutralized to 1.0", row_2023["explanation"])
        self.assertIn("ex-GMI", row_2023["explanation"])

    def test_adapted_altman_cash_substitution_and_pre_ipo(self):
        """Test Cash/TA substitution and graceful handling of pre-IPO periods."""
        mock_fin = pd.DataFrame([
            {"cal_year": 2021, "line_item": "total_assets", "value": 500.0, "fiscal_period_end": "2021-12-31"},
            {"cal_year": 2021, "line_item": "total_liabilities", "value": 300.0, "fiscal_period_end": "2021-12-31"},
            {"cal_year": 2021, "line_item": "retained_earnings", "value": -50.0, "fiscal_period_end": "2021-12-31"},
            {"cal_year": 2021, "line_item": "revenue", "value": 150.0, "fiscal_period_end": "2021-12-31"},
            {"cal_year": 2021, "line_item": "net_income", "value": -10.0, "fiscal_period_end": "2021-12-31"},
            {"cal_year": 2021, "line_item": "interest_expense", "value": 5.0, "fiscal_period_end": "2021-12-31"},
            {"cal_year": 2021, "line_item": "income_tax_expense", "value": 0.0, "fiscal_period_end": "2021-12-31"},
        ])
        # Pre-IPO market data
        mock_mkt = pd.DataFrame([
            {"ticker": "SEZL", "cal_year": 2021, "market_cap": float("nan"), "is_pre_ipo": 1, "data_quality": "PRE_IPO_UNAVAILABLE"}
        ])

        results = compute_adapted_altman_for_company("SEZL", "0001662991", mock_fin, mock_mkt)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["classification"], "PRE_IPO_UNAVAILABLE")
        self.assertIn("Pre-IPO", results[0]["score_formatted"])

    def test_accruals_ratio_calculation(self):
        """Test (NI - CFO) / Total Assets calculation and risk zones."""
        mock_fin = pd.DataFrame([
            {"cal_year": 2024, "line_item": "net_income", "value": 100.0, "fiscal_period_end": "2024-12-31"},
            {"cal_year": 2024, "line_item": "operating_cash_flow", "value": 20.0, "fiscal_period_end": "2024-12-31"},
            {"cal_year": 2024, "line_item": "total_assets", "value": 500.0, "fiscal_period_end": "2024-12-31"},
        ])
        results = compute_accruals_for_company("TEST", "0000000000", mock_fin)
        self.assertEqual(len(results), 1)
        # Accruals = (100 - 20) / 500 = 80 / 500 = +0.16 -> HIGH_ACCRUALS_RISK
        self.assertAlmostEqual(results[0]["score_value"], 0.16)
        self.assertEqual(results[0]["classification"], "HIGH_ACCRUALS_RISK")

    def test_divergence_exemption_pgy_enva(self):
        """Test that PGY and ENVA receive explicit N/A for growth divergence."""
        mock_data = pd.DataFrame([
            {"cal_year": 2023, "line_item": "revenue", "value": 100.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2023, "line_item": "receivables", "value": 50.0, "fiscal_period_end": "2023-12-31"},
            {"cal_year": 2024, "line_item": "revenue", "value": 120.0, "fiscal_period_end": "2024-12-31"},
            {"cal_year": 2024, "line_item": "receivables", "value": 80.0, "fiscal_period_end": "2024-12-31"},
        ])

        results_pgy = compute_divergence_for_company("PGY", "0001857140", mock_data)
        self.assertTrue(all("securitized/fair-value" in r["score_formatted"] for r in results_pgy))
        self.assertTrue(all(r["classification"] == "NOT_APPLICABLE" for r in results_pgy))

        results_enva = compute_divergence_for_company("ENVA", "0001529849", mock_data)
        self.assertTrue(all("securitized/fair-value" in r["score_formatted"] for r in results_enva))
        self.assertTrue(all(r["classification"] == "NOT_APPLICABLE" for r in results_enva))

    def test_database_persistence_and_row_counts(self):
        """Verify that SQLite and CSV contain exactly 216 rows across 9 companies x 4 models."""
        df_sql = read_anomalies()
        self.assertEqual(len(df_sql), 216)
        self.assertEqual(df_sql["ticker"].nunique(), 9)
        self.assertEqual(df_sql["anomaly_name"].nunique(), 4)

        df_csv = pd.read_csv(ANOMALIES_CSV_PATH)
        self.assertEqual(len(df_csv), 216)

    def test_phase3_outlier_cross_correlation(self):
        """Verify cross-correlation linking Phase 3 distress outliers with Phase 4 anomaly scores."""
        anomalies_df = read_anomalies()
        ratios_df = read_ratios()
        corr_df = audit_phase3_cross_correlation(anomalies_df, ratios_df)
        self.assertFalse(corr_df.empty)
        # Check that AFRM, OPRT, PGY, SEZL, SOFI, UPST distress rows are mapped
        flagged_tickers = corr_df["ticker"].unique().tolist()
        for expected in ["AFRM", "OPRT", "PGY", "SEZL", "SOFI", "UPST"]:
            self.assertIn(expected, flagged_tickers)


if __name__ == "__main__":
    unittest.main()
