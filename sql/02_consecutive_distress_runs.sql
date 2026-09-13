-- =============================================================================
-- Query 2: Multi-Year Chronic Runs in the Altman Z Distress Zone
-- =============================================================================
-- Analytical Question:
--   Which specialty lenders suffered chronic, consecutive-year distress
--   under the Adapted Altman Z-Score (< 1.81), and which experienced
--   cyclical vs. structural balance-sheet fragility?
--
-- Forensic Context:
--   Consumer lenders operate with high leverage, but well-capitalized lenders
--   (such as Sezzle with Z > 8.0) manage liquidity buffers effectively.
--   Companies trapped in the Distress Zone for 3+ consecutive years represent
--   structural solvency concerns, while Upstart exhibited a cyclical 2-year run
--   (2022-2023) followed by a 2025 relapse.
--
-- SQL Techniques:
--   - Multi-period window functions: LAG() and LEAD() OVER (PARTITION BY ticker)
--   - Run detection logic combining adjacent state comparisons
--   - Group aggregation with string accumulation (GROUP_CONCAT)
-- =============================================================================

WITH z_scores AS (
    SELECT
        ticker,
        cal_year,
        score_value AS altman_z,
        classification,
        LAG(classification) OVER (PARTITION BY ticker ORDER BY cal_year) AS prev_class,
        LEAD(classification) OVER (PARTITION BY ticker ORDER BY cal_year) AS next_class
    FROM anomalies
    WHERE anomaly_name = 'adapted_altman_z_score'
),
distress_streaks AS (
    SELECT
        ticker,
        cal_year,
        ROUND(altman_z, 2) AS altman_z,
        classification,
        prev_class,
        next_class,
        CASE 
            WHEN classification = 'DISTRESS_ZONE' AND (prev_class = 'DISTRESS_ZONE' OR next_class = 'DISTRESS_ZONE')
            THEN 1 
            ELSE 0 
        END AS is_consecutive_distress
    FROM z_scores
)
SELECT
    ticker,
    COUNT(CASE WHEN classification = 'DISTRESS_ZONE' THEN 1 END) AS total_distress_years,
    COUNT(CASE WHEN is_consecutive_distress = 1 THEN 1 END) AS consecutive_distress_years,
    GROUP_CONCAT(CASE WHEN is_consecutive_distress = 1 THEN cal_year END, ', ') AS consecutive_distress_years_list,
    ROUND(AVG(CASE WHEN is_consecutive_distress = 1 THEN altman_z END), 2) AS avg_distress_z_score,
    CASE 
        WHEN COUNT(CASE WHEN is_consecutive_distress = 1 THEN 1 END) >= 3 THEN 'CHRONIC / STRUCTURAL DISTRESS'
        WHEN COUNT(CASE WHEN is_consecutive_distress = 1 THEN 1 END) = 2 THEN 'CYCLICAL MULTI-YEAR DISTRESS'
        ELSE 'ISOLATED / SAFE'
    END AS distress_severity_tier
FROM distress_streaks
GROUP BY ticker
HAVING consecutive_distress_years >= 2
ORDER BY consecutive_distress_years DESC, avg_distress_z_score ASC;
