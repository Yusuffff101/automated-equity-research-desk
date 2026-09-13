-- =============================================================================
-- Query 4: Unified Multi-Table Risk Matrix (Ratios + Anomalies)
-- =============================================================================
-- Analytical Question:
--   What is the cross-sectional risk profile for every company in the universe,
--   combining profitability, credit leverage, and forensic distress metrics?
--
-- Forensic Context:
--   Sell-side and buy-side analysts synthesize multiple disparate tables to
--   spot concurrent fragility—e.g. where low solvency (Altman Z < 1.81) aligns
--   with negative cash generation (high non-cash accruals ratio > 0.05).
--
-- SQL Techniques:
--   - Two parallel CTEs pivoting the `ratios` and `anomalies` tables
--   - Multi-key INNER JOIN on (ticker, cal_year)
--   - Compound classification logic assigning a composite risk tier
-- =============================================================================

WITH ratio_pivots AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN ratio_name = 'roe' THEN value END) AS roe,
        MAX(CASE WHEN ratio_name = 'debt_to_equity' THEN value END) AS debt_to_equity,
        MAX(CASE WHEN ratio_name = 'interest_coverage' THEN value END) AS interest_coverage
    FROM ratios
    GROUP BY ticker, cal_year
),
anomaly_pivots AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN anomaly_name = 'adapted_altman_z_score' THEN score_value END) AS altman_z,
        MAX(CASE WHEN anomaly_name = 'adapted_altman_z_score' THEN classification END) AS altman_z_class,
        MAX(CASE WHEN anomaly_name = 'adapted_beneish_m_score' THEN score_value END) AS beneish_m,
        MAX(CASE WHEN anomaly_name = 'adapted_beneish_m_score' THEN classification END) AS beneish_m_class,
        MAX(CASE WHEN anomaly_name = 'accruals_ratio' THEN score_value END) AS accruals_ratio,
        MAX(CASE WHEN anomaly_name = 'accruals_ratio' THEN classification END) AS accruals_class
    FROM anomalies
    GROUP BY ticker, cal_year
)
SELECT
    r.ticker,
    r.cal_year,
    ROUND(r.roe * 100, 2) || '%' AS roe,
    ROUND(r.debt_to_equity, 2) || 'x' AS debt_to_equity,
    CASE 
        WHEN r.interest_coverage IS NULL THEN 'N/A'
        ELSE ROUND(r.interest_coverage, 2) || 'x'
    END AS interest_coverage,
    ROUND(a.altman_z, 2) AS altman_z,
    a.altman_z_class,
    CASE 
        WHEN a.beneish_m IS NULL THEN 'N/A' 
        ELSE CAST(ROUND(a.beneish_m, 2) AS TEXT) 
    END AS beneish_m,
    ROUND(a.accruals_ratio, 3) AS accruals_ratio,
    CASE
        WHEN a.altman_z_class = 'DISTRESS_ZONE' AND a.accruals_ratio > 0.05 THEN 'HIGH CONCURRENT RISK'
        WHEN a.altman_z_class = 'DISTRESS_ZONE' THEN 'ELEVATED SOLVENCY RISK'
        WHEN a.altman_z_class = 'SAFE_ZONE' THEN 'HEALTHY'
        ELSE 'MODERATE'
    END AS composite_risk_tier
FROM ratio_pivots r
JOIN anomaly_pivots a 
  ON r.ticker = a.ticker AND r.cal_year = a.cal_year
WHERE r.cal_year = 2025
ORDER BY a.altman_z ASC;
