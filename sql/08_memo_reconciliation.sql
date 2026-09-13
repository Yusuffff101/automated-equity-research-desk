-- 08_memo_reconciliation.sql
-- Automated Equity Research Desk | Verification & Data Integrity Suite
-- 
-- ANALYTICAL OBJECTIVE:
-- Reconcile every fundamental, ratio, anomaly score, and valuation metric
-- cited in the UPST Investment Memo against the canonical financials.db database.
-- Surfaces any variance between reported memo claims and database truth.

WITH fin_piv AS (
    SELECT 
        ticker,
        cal_year,
        MAX(CASE WHEN line_item = 'revenue' THEN value END) AS revenue,
        MAX(CASE WHEN line_item = 'net_income' THEN value END) AS net_income,
        MAX(CASE WHEN line_item = 'operating_cash_flow' THEN value END) AS operating_cash_flow,
        MAX(CASE WHEN line_item = 'total_debt' THEN value END) AS total_debt,
        MAX(CASE WHEN line_item = 'total_liabilities' THEN value END) AS total_liabilities,
        MAX(CASE WHEN line_item = 'shareholders_equity' THEN value END) AS shareholders_equity,
        MAX(CASE WHEN line_item = 'total_assets' THEN value END) AS total_assets,
        MAX(CASE WHEN line_item = 'ebit' THEN value END) AS ebit,
        MAX(CASE WHEN line_item = 'receivables' THEN value END) AS receivables
    FROM financials
    WHERE ticker = 'UPST'
    GROUP BY ticker, cal_year
),
rat_piv AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN ratio_name = 'debt_to_equity' THEN value END) AS debt_to_equity,
        MAX(CASE WHEN ratio_name = 'roe' THEN value END) AS roe,
        MAX(CASE WHEN ratio_name = 'roa' THEN value END) AS roa,
        MAX(CASE WHEN ratio_name = 'interest_coverage' THEN value END) AS interest_coverage
    FROM ratios
    WHERE ticker = 'UPST'
    GROUP BY ticker, cal_year
),
anom_piv AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN anomaly_name = 'adapted_altman_z_score' THEN score_value END) AS altman_z,
        MAX(CASE WHEN anomaly_name = 'adapted_beneish_m_score' THEN score_value END) AS beneish_m,
        MAX(CASE WHEN anomaly_name = 'accruals_ratio' THEN score_value END) AS accruals_ratio,
        MAX(CASE WHEN anomaly_name = 'growth_divergence' THEN score_value END) AS growth_divergence
    FROM anomalies
    WHERE ticker = 'UPST'
    GROUP BY ticker, cal_year
)
SELECT
    f.cal_year,
    ROUND(f.revenue / 1e6, 2) AS revenue_m,
    ROUND(f.net_income / 1e6, 2) AS net_income_m,
    ROUND(f.operating_cash_flow / 1e6, 2) AS cfo_m,
    ROUND(f.total_debt / 1e6, 2) AS total_debt_m,
    ROUND(f.total_liabilities / 1e6, 2) AS total_liabilities_m,
    ROUND(f.shareholders_equity / 1e6, 2) AS equity_m,
    ROUND(r.debt_to_equity, 2) AS debt_to_equity,
    ROUND(r.roe * 100.0, 2) AS roe_pct,
    ROUND(r.roa * 100.0, 2) AS roa_pct,
    ROUND(a.accruals_ratio, 3) AS accruals_ratio,
    ROUND(a.altman_z, 2) AS altman_z,
    ROUND(a.beneish_m, 2) AS beneish_m,
    ROUND(a.growth_divergence * 100.0, 1) AS divergence_pct,
    ROUND(m.market_cap / 1e9, 2) AS market_cap_b,
    ROUND(m.close_price, 2) AS close_price
FROM fin_piv f
LEFT JOIN rat_piv r ON f.ticker = r.ticker AND f.cal_year = r.cal_year
LEFT JOIN anom_piv a ON f.ticker = a.ticker AND f.cal_year = a.cal_year
LEFT JOIN market_data m ON f.ticker = m.ticker AND f.cal_year = m.cal_year
WHERE f.cal_year BETWEEN 2021 AND 2025
ORDER BY f.cal_year;
