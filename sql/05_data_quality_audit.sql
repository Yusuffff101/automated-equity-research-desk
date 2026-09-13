-- =============================================================================
-- Query 5: SEC EDGAR Data Quality & 10-K/A Restatement Audit
-- =============================================================================
-- Analytical Question:
--   How are financial statement facts distributed across data quality flags,
--   and which companies exhibit elevated 10-K/A amendment and restatement rates?
--
-- Forensic Context:
--   Phase 2 separated benign comparative prior-period disclosures (COMPARATIVE)
--   from genuine accounting restatements and amendments (RESTATED).
--   Pagaya Technologies (PGY) exhibits a 26.7% restatement rate from 10-K/A
--   filings, while Sezzle (14.4%) reflects IPO restatement recasts.
--
-- SQL Techniques:
--   - Conditional aggregation with COUNT(CASE WHEN ...)
--   - Mathematical ratio calculations casting integers to REAL
--   - Categorical assignment of reporting stability tiers
-- =============================================================================

SELECT
    ticker,
    COUNT(*) AS total_facts,
    COUNT(CASE WHEN data_quality = 'OK' THEN 1 END) AS count_ok,
    COUNT(CASE WHEN data_quality = 'COMPARATIVE' THEN 1 END) AS count_comparative,
    COUNT(CASE WHEN data_quality = 'RESTATED' THEN 1 END) AS count_restated,
    COUNT(CASE WHEN data_quality LIKE 'FALLBACK%' THEN 1 END) AS count_fallback,
    COUNT(CASE WHEN data_quality = 'MISSING_TAG' THEN 1 END) AS count_missing,
    ROUND(
        (CAST(COUNT(CASE WHEN data_quality = 'RESTATED' THEN 1 END) AS REAL) / COUNT(*)) * 100, 
        2
    ) AS restatement_pct,
    CASE 
        WHEN COUNT(CASE WHEN data_quality = 'RESTATED' THEN 1 END) > 5 THEN 'HIGH AMENDMENT FREQUENCY'
        WHEN COUNT(CASE WHEN data_quality = 'RESTATED' THEN 1 END) > 0 THEN 'MODERATE RESTATED FACTS'
        ELSE 'ZERO RESTATEMENTS'
    END AS reporting_stability
FROM financials
GROUP BY ticker
ORDER BY count_restated DESC, total_facts DESC;
