-- =============================================================================
-- Query 6: Cross-Sectional Relative Valuation Multiples (P/S, P/B, P/E)
-- =============================================================================
-- Analytical Question:
--   What are the peer valuation multiples across the fintech universe in pure
--   SQL, and how large is UPST's multiple premium over profitable comps?
--
-- Forensic Context:
--   Validates the Step 1 Phase 6 valuation table entirely natively in SQL.
--   UPST trades at 4.22x P/S and 82.25x P/E, commanding a massive premium
--   over profitable credit comps like Enova (12.8x P/E) and OneMain (10.2x P/E).
--
-- SQL Techniques:
--   - Pivot CTE aggregating revenue, net income, and equity from `financials`
--   - INNER JOIN with `market_data` on (ticker, cal_year)
--   - Valuation multiple arithmetic with conditional NULL handling for negative earnings
-- =============================================================================

WITH fin_pivots AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN line_item = 'revenue' THEN value END) AS revenue,
        MAX(CASE WHEN line_item = 'net_income' THEN value END) AS net_income,
        MAX(CASE WHEN line_item = 'shareholders_equity' THEN value END) AS equity
    FROM financials
    GROUP BY ticker, cal_year
)
SELECT
    m.ticker,
    m.cal_year,
    ROUND(m.market_cap / 1e9, 2) AS market_cap_b,
    ROUND(f.revenue / 1e6, 1) AS revenue_m,
    ROUND(f.net_income / 1e6, 1) AS net_income_m,
    ROUND(f.equity / 1e6, 1) AS equity_m,
    ROUND(m.market_cap / f.revenue, 2) AS ps_multiple,
    ROUND(m.market_cap / f.equity, 2) AS pb_multiple,
    CASE 
        WHEN f.net_income > 0 THEN ROUND(m.market_cap / f.net_income, 2)
        ELSE NULL
    END AS pe_multiple,
    CASE 
        WHEN (m.market_cap / f.revenue) > 4.0 THEN 'PREMIUM VALUATION (> 4x P/S)'
        WHEN (m.market_cap / f.revenue) < 1.0 THEN 'DEEP DISCOUNT (< 1x P/S)'
        ELSE 'FAIR / IN-LINE'
    END AS valuation_tier
FROM market_data m
JOIN fin_pivots f 
  ON m.ticker = f.ticker AND m.cal_year = f.cal_year
WHERE m.cal_year = 2025
ORDER BY ps_multiple DESC;
