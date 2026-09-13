-- =============================================================================
-- Query 3: Peer Ranking by Forensic Earnings Manipulation Risk (Adapted Beneish)
-- =============================================================================
-- Analytical Question:
--   How do companies rank across the peer group in earnings manipulation risk
--   each calendar year, and which entity surfaced as the highest risk outlier?
--
-- Forensic Context:
--   The Adapted Beneish M-Score evaluates 7 financial statement indices
--   (excluding Gross Margin Index per sector adaptation). A higher (less negative
--   or positive) M-Score denotes aggressive accounting, uncollected accruals,
--   or asset inflation. In 2022, UPST ranked #1 with M = +1.28 (> -1.78 threshold).
--
-- SQL Techniques:
--   - Window function: DENSE_RANK() OVER (PARTITION BY cal_year ORDER BY score_value DESC)
--   - Text formatting and substring truncation for forensic explanation previews
-- =============================================================================

WITH ranked_beneish AS (
    SELECT
        cal_year,
        ticker,
        score_value AS beneish_m_score,
        classification,
        explanation,
        DENSE_RANK() OVER (
            PARTITION BY cal_year 
            ORDER BY 
                CASE WHEN score_value IS NULL THEN -999 ELSE score_value END DESC
        ) AS manipulation_risk_rank
    FROM anomalies
    WHERE anomaly_name = 'adapted_beneish_m_score'
      AND score_value IS NOT NULL
)
SELECT
    cal_year,
    manipulation_risk_rank,
    ticker,
    ROUND(beneish_m_score, 2) AS beneish_m_score,
    classification,
    SUBSTR(explanation, 1, 65) || '...' AS forensic_rationale
FROM ranked_beneish
WHERE cal_year >= 2022
ORDER BY cal_year ASC, manipulation_risk_rank ASC;
