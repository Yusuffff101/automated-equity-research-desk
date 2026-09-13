-- =============================================================================
-- Query 7: Earnings Decoupling & Operating Cash Burn Audit
-- =============================================================================
-- Analytical Question:
--   Which company-years exhibited deceptive accounting health—reporting positive
--   GAAP net income while operating cash flow (CFO) burned negative?
--
-- Forensic Context:
--   Sloan (1996) established that high non-cash accruals decay rapidly and
--   predict future earnings underperformance. Upstart's 2025 "recovery"
--   produced $+53.6M of GAAP profit unbacked by cash ($-147.7M CFO), creating
--   $+201.3M in non-cash accruals (+6.8% of assets).
--
-- SQL Techniques:
--   - Pivot CTE comparing GAAP Net Income against Operating Cash Flow
--   - Accruals calculation: (Net Income - CFO) / Total Assets
--   - Threshold filtering isolating critical cash decoupling
-- =============================================================================

WITH cash_vs_accruals AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN line_item = 'net_income' THEN value END) AS net_income,
        MAX(CASE WHEN line_item = 'operating_cash_flow' THEN value END) AS cfo,
        MAX(CASE WHEN line_item = 'total_assets' THEN value END) AS total_assets
    FROM financials
    GROUP BY ticker, cal_year
)
SELECT
    ticker,
    cal_year,
    ROUND(net_income / 1e6, 1) AS net_income_m,
    ROUND(cfo / 1e6, 1) AS operating_cash_flow_m,
    ROUND((net_income - cfo) / 1e6, 1) AS non_cash_accruals_m,
    ROUND(((net_income - cfo) / total_assets), 3) AS accruals_ratio_tata,
    CASE 
        WHEN net_income > 0 AND cfo < 0 THEN 'CRITICAL: PROFIT WITH CASH DRAIN'
        WHEN net_income < 0 AND cfo < 0 THEN 'CASH BURN / STRUCTURAL LOSS'
        WHEN net_income > 0 AND cfo >= net_income THEN 'HIGH QUALITY: CASH-BACKED EARNINGS'
        ELSE 'NORMAL WORKING CAPITAL ACCRUAL'
    END AS earnings_quality_signal
FROM cash_vs_accruals
WHERE net_income IS NOT NULL AND cfo IS NOT NULL
ORDER BY non_cash_accruals_m DESC;
