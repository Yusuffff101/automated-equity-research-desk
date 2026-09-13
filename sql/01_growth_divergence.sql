-- =============================================================================
-- Query 1: YoY Revenue Growth vs. YoY Receivables Growth Divergence
-- =============================================================================
-- Analytical Question:
--   Which company-years experienced an abnormal decoupling between receivables
--   buildup and revenue growth (e.g. Upstart's 2022 loan inventory surge)?
--
-- Forensic Context:
--   When loan buyers pull back in credit tightenings, originate-to-distribute
--   platforms are forced to hold uncommitted loans on their balance sheet. This
--   causes uncollected receivables to surge while revenue stalls or contracts,
--   driving a massive positive divergence spread.
--
-- SQL Techniques:
--   - Common Table Expressions (CTEs) to pivot line items
--   - Window functions: LAG() OVER (PARTITION BY ticker ORDER BY cal_year)
--   - Conditional CASE logic for anomaly threshold classification
-- =============================================================================

WITH pivoted_financials AS (
    SELECT
        ticker,
        cal_year,
        MAX(CASE WHEN line_item = 'revenue' THEN value END) AS revenue,
        MAX(CASE WHEN line_item = 'receivables' THEN value END) AS receivables
    FROM financials
    GROUP BY ticker, cal_year
),
growth_calc AS (
    SELECT
        ticker,
        cal_year,
        revenue,
        receivables,
        LAG(revenue) OVER (PARTITION BY ticker ORDER BY cal_year) AS prior_revenue,
        LAG(receivables) OVER (PARTITION BY ticker ORDER BY cal_year) AS prior_receivables
    FROM pivoted_financials
)
SELECT
    ticker,
    cal_year,
    ROUND(revenue / 1e6, 1) AS revenue_m,
    ROUND(receivables / 1e6, 1) AS receivables_m,
    ROUND(((revenue - prior_revenue) / prior_revenue) * 100, 2) AS rev_growth_pct,
    ROUND(((receivables - prior_receivables) / prior_receivables) * 100, 2) AS rec_growth_pct,
    ROUND((((receivables - prior_receivables) / prior_receivables) - ((revenue - prior_revenue) / prior_revenue)) * 100, 2) AS divergence_spread_pct,
    CASE 
        WHEN (((receivables - prior_receivables) / prior_receivables) - ((revenue - prior_revenue) / prior_revenue)) * 100 > 30.0 
        THEN 'FLAG: RECEIVABLES SURGE'
        WHEN (((receivables - prior_receivables) / prior_receivables) - ((revenue - prior_revenue) / prior_revenue)) * 100 < -30.0 
        THEN 'INVENTORY OFFLOAD'
        ELSE 'NORMAL'
    END AS divergence_signal
FROM growth_calc
WHERE prior_revenue IS NOT NULL AND prior_receivables IS NOT NULL
ORDER BY divergence_spread_pct DESC;
