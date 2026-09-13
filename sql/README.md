# 🏛️ SQL Analytics Showcase: Automated Equity Research Desk

This directory showcases **7 production analytical SQL queries** executed directly against the local SQLite warehouse ([`data/normalized/financials.db`](../data/normalized/financials.db)).

Rather than trivial `SELECT *` filtering, each query addresses a specific fundamental research question using advanced SQL techniques: **window functions (`LAG`, `LEAD`, `DENSE_RANK`)**, **multi-table Common Table Expressions (CTEs)**, **conditional aggregation**, and **cross-table JOINs**.

---

## 📋 Query Index

| Query | File | Analytical Theme | Advanced SQL Technique |
|:---:|:---|:---|:---|
| **1** | [`01_growth_divergence.sql`](./01_growth_divergence.sql) | Query 1: Revenue vs. Receivables Growth Divergence | CTEs + Window function LAG() OVER (PARTITION BY ticker ORDER BY cal_year) |
| **2** | [`02_consecutive_distress_runs.sql`](./02_consecutive_distress_runs.sql) | Query 2: Multi-Year Chronic Runs in the Altman Z Distress Zone | Window functions LAG() & LEAD() detecting sequential distress states + GROUP_CONCAT |
| **3** | [`03_beneish_rankings.sql`](./03_beneish_rankings.sql) | Query 3: Peer Ranking by Forensic Earnings Manipulation Risk (Beneish M-Score) | Window function DENSE_RANK() OVER (PARTITION BY cal_year ORDER BY score_value DESC) |
| **4** | [`04_composite_risk_profile.sql`](./04_composite_risk_profile.sql) | Query 4: Unified Multi-Table Risk Matrix (Ratios + Anomalies) | Multi-table CTEs joining `ratios` and `anomalies` on (ticker, cal_year) with composite tier logic |
| **5** | [`05_data_quality_audit.sql`](./05_data_quality_audit.sql) | Query 5: SEC EDGAR Data Quality & 10-K/A Restatement Audit | Conditional aggregation COUNT(CASE WHEN ...) computing restatement percentages |
| **6** | [`06_relative_valuation_multiples.sql`](./06_relative_valuation_multiples.sql) | Query 6: Cross-Sectional Relative Valuation Multiples (P/S, P/B, P/E) | Multi-table JOIN between `market_data` and pivot CTE of `financials` |
| **7** | [`07_accruals_earnings_decoupling.sql`](./07_accruals_earnings_decoupling.sql) | Query 7: Earnings Decoupling & Operating Cash Burn Audit | Pivot CTE comparing Net Income against CFO and computing non-cash accruals magnitude |

---

## Query 1: Revenue vs. Receivables Growth Divergence

**File:** [`sql/01_growth_divergence.sql`](./01_growth_divergence.sql)  
**Analytical Objective:** Which company-years experienced an abnormal decoupling between receivables buildup and revenue growth?  
**SQL Features:** `CTEs + Window function LAG() OVER (PARTITION BY ticker ORDER BY cal_year)`  

### SQL Implementation
```sql
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
```

### Query Results (Sample Top 10 Rows)

| ticker   |   cal_year |   revenue_m |   receivables_m |   rev_growth_pct |   rec_growth_pct |   divergence_spread_pct | divergence_signal       |
|:---------|-----------:|------------:|----------------:|-----------------:|-----------------:|------------------------:|:------------------------|
| UPST     |       2022 |       842.4 |          1010.4 |            -0.72 |           300.2  |                  300.93 | FLAG: RECEIVABLES SURGE |
| SOFI     |       2023 |       421.5 |           836.2 |            11.76 |           171.52 |                  159.76 | FLAG: RECEIVABLES SURGE |
| SOFI     |       2022 |       377.1 |           308   |            52.23 |           165.68 |                  113.45 | FLAG: RECEIVABLES SURGE |
| AFRM     |       2023 |      1588   |          4198.4 |            17.69 |            78.8  |                   61.11 | FLAG: RECEIVABLES SURGE |
| UPST     |       2023 |       513.6 |          1156.4 |           -39.04 |            14.45 |                   53.49 | FLAG: RECEIVABLES SURGE |
| SOFI     |       2024 |       503.1 |          1246.5 |            19.38 |            49.07 |                   29.69 | NORMAL                  |
| OMF      |       2023 |      4564   |         18098   |             2.91 |             6.92 |                    4.02 | NORMAL                  |
| AFRM     |       2026 |      4261.1 |          8997.4 |            32.15 |            35.74 |                    3.59 | NORMAL                  |
| OMF      |       2022 |      4435   |         16926   |             1.63 |             3.48 |                    1.86 | NORMAL                  |
| OMF      |       2024 |      4993   |         20083   |             9.4  |            10.97 |                    1.57 | NORMAL                  |

---

## Query 2: Multi-Year Chronic Runs in the Altman Z Distress Zone

**File:** [`sql/02_consecutive_distress_runs.sql`](./02_consecutive_distress_runs.sql)  
**Analytical Objective:** Which specialty lenders suffered chronic, multi-year runs in the Distress Zone (Z < 1.81) vs. cyclical fragility?  
**SQL Features:** `Window functions LAG() & LEAD() detecting sequential distress states + GROUP_CONCAT`  

### SQL Implementation
```sql
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
```

### Query Results (All 7 Rows)

| ticker   |   total_distress_years |   consecutive_distress_years | consecutive_distress_years_list   |   avg_distress_z_score | distress_severity_tier        |
|:---------|-----------------------:|-----------------------------:|:----------------------------------|-----------------------:|:------------------------------|
| LC       |                      5 |                            5 | 2021, 2022, 2023, 2024, 2025      |                   0.28 | CHRONIC / STRUCTURAL DISTRESS |
| OPRT     |                      5 |                            5 | 2021, 2022, 2023, 2024, 2025      |                   0.42 | CHRONIC / STRUCTURAL DISTRESS |
| SOFI     |                      5 |                            5 | 2021, 2022, 2023, 2024, 2025      |                   0.6  | CHRONIC / STRUCTURAL DISTRESS |
| OMF      |                      5 |                            5 | 2021, 2022, 2023, 2024, 2025      |                   0.82 | CHRONIC / STRUCTURAL DISTRESS |
| AFRM     |                      4 |                            4 | 2022, 2023, 2024, 2025            |                   0.62 | CHRONIC / STRUCTURAL DISTRESS |
| ENVA     |                      4 |                            4 | 2022, 2023, 2024, 2025            |                   1.65 | CHRONIC / STRUCTURAL DISTRESS |
| UPST     |                      3 |                            2 | 2022, 2023                        |                   1.06 | CYCLICAL MULTI-YEAR DISTRESS  |

---

## Query 3: Peer Ranking by Forensic Earnings Manipulation Risk (Beneish M-Score)

**File:** [`sql/03_beneish_rankings.sql`](./03_beneish_rankings.sql)  
**Analytical Objective:** How do companies rank across the peer group in earnings manipulation risk each calendar year?  
**SQL Features:** `Window function DENSE_RANK() OVER (PARTITION BY cal_year ORDER BY score_value DESC)`  

### SQL Implementation
```sql
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
```

### Query Results (Sample Top 12 Rows)

|   cal_year |   manipulation_risk_rank | ticker   |   beneish_m_score | classification             | forensic_rationale                                                   |
|-----------:|-------------------------:|:---------|------------------:|:---------------------------|:---------------------------------------------------------------------|
|       2022 |                        1 | UPST     |              1.28 | ELEVATED_MANIPULATION_RISK | Adapted M-Score (ex-GMI, financial institution adjustment) = 1.28... |
|       2022 |                        2 | SOFI     |             -0.01 | ELEVATED_MANIPULATION_RISK | Adapted M-Score (ex-GMI, financial institution adjustment) = -0.0... |
|       2022 |                        3 | LC       |             -1.98 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -1.9... |
|       2022 |                        4 | OPRT     |             -2.55 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -2.5... |
|       2022 |                        5 | AFRM     |             -2.65 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -2.6... |
|       2022 |                        6 | OMF      |             -2.89 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -2.8... |
|       2022 |                        7 | ENVA     |             -2.99 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -2.9... |
|       2022 |                        8 | SEZL     |             -3.98 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -3.9... |
|       2023 |                        1 | SOFI     |             -0.29 | ELEVATED_MANIPULATION_RISK | Adapted M-Score (ex-GMI, financial institution adjustment) = -0.2... |
|       2023 |                        2 | SEZL     |             -1.79 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -1.7... |
|       2023 |                        3 | LC       |             -2    | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -2.0... |
|       2023 |                        4 | UPST     |             -2.44 | LOW_MANIPULATION_RISK      | Adapted M-Score (ex-GMI, financial institution adjustment) = -2.4... |

---

## Query 4: Unified Multi-Table Risk Matrix (Ratios + Anomalies)

**File:** [`sql/04_composite_risk_profile.sql`](./04_composite_risk_profile.sql)  
**Analytical Objective:** What is the cross-sectional risk profile for every company in the universe in FY2025?  
**SQL Features:** `Multi-table CTEs joining `ratios` and `anomalies` on (ticker, cal_year) with composite tier logic`  

### SQL Implementation
```sql
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
```

### Query Results (All 9 Rows)

| ticker   |   cal_year | roe    | debt_to_equity   | interest_coverage   |   altman_z | altman_z_class   |   beneish_m |   accruals_ratio | composite_risk_tier    |
|:---------|-----------:|:-------|:-----------------|:--------------------|-----------:|:-----------------|------------:|-----------------:|:-----------------------|
| LC       |       2025 | 9.04%  | 0.0x             | 1.53x               |       0.34 | DISTRESS_ZONE    |       -1.62 |            0.247 | HIGH CONCURRENT RISK   |
| OPRT     |       2025 | 6.47%  | 1.2x             | 1.19x               |       0.56 | DISTRESS_ZONE    |       -3.17 |           -0.119 | ELEVATED SOLVENCY RISK |
| SOFI     |       2025 | 4.59%  | 0.17x            | N/A                 |       0.65 | DISTRESS_ZONE    |       -2.12 |            0.083 | HIGH CONCURRENT RISK   |
| OMF      |       2025 | 23.02% | 6.67x            | 1.79x               |       0.84 | DISTRESS_ZONE    |       -2.94 |           -0.086 | ELEVATED SOLVENCY RISK |
| AFRM     |       2025 | 1.7%   | 2.48x            | -0.21x              |       1.65 | DISTRESS_ZONE    |       -2.67 |           -0.066 | ELEVATED SOLVENCY RISK |
| UPST     |       2025 | 6.71%  | 2.29x            | N/A                 |       1.71 | DISTRESS_ZONE    |       -2.04 |            0.068 | HIGH CONCURRENT RISK   |
| ENVA     |       2025 | 23.07% | 3.37x            | 2.18x               |       1.77 | DISTRESS_ZONE    |       -3.42 |           -0.234 | ELEVATED SOLVENCY RISK |
| PGY      |       2025 | 16.96% | 0.4x             | N/A                 |       1.87 | GREY_ZONE        |       -2.83 |           -0.102 | MODERATE               |
| SEZL     |       2025 | 78.4%  | 0.82x            | N/A                 |       8.55 | SAFE_ZONE        |       -2.84 |           -0.192 | HEALTHY                |

---

## Query 5: SEC EDGAR Data Quality & 10-K/A Restatement Audit

**File:** [`sql/05_data_quality_audit.sql`](./05_data_quality_audit.sql)  
**Analytical Objective:** How are financial statement facts distributed across data quality flags, and which companies exhibit elevated 10-K/A restatement rates?  
**SQL Features:** `Conditional aggregation COUNT(CASE WHEN ...) computing restatement percentages`  

### SQL Implementation
```sql
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
```

### Query Results (All 9 Rows)

| ticker   |   total_facts |   count_ok |   count_comparative |   count_restated |   count_fallback |   count_missing |   restatement_pct | reporting_stability      |
|:---------|--------------:|-----------:|--------------------:|-----------------:|-----------------:|----------------:|------------------:|:-------------------------|
| PGY      |            90 |         14 |                  11 |               24 |                3 |              38 |             26.67 | HIGH AMENDMENT FREQUENCY |
| SEZL     |            90 |         12 |                  34 |               13 |                6 |              25 |             14.44 | HIGH AMENDMENT FREQUENCY |
| OMF      |            90 |          8 |                  24 |                8 |               15 |              35 |              8.89 | HIGH AMENDMENT FREQUENCY |
| AFRM     |            90 |         12 |                  40 |                5 |               15 |              18 |              5.56 | MODERATE RESTATED FACTS  |
| UPST     |            90 |         10 |                  36 |                2 |               10 |              32 |              2.22 | MODERATE RESTATED FACTS  |
| LC       |            90 |         10 |                  30 |                1 |               10 |              37 |              1.11 | MODERATE RESTATED FACTS  |
| SOFI     |            90 |          9 |                  31 |                1 |               12 |              37 |              1.11 | MODERATE RESTATED FACTS  |
| ENVA     |            90 |         12 |                  48 |                0 |                0 |              30 |              0    | ZERO RESTATEMENTS        |
| OPRT     |            90 |          8 |                  32 |                0 |               10 |              40 |              0    | ZERO RESTATEMENTS        |

---

## Query 6: Cross-Sectional Relative Valuation Multiples (P/S, P/B, P/E)

**File:** [`sql/06_relative_valuation_multiples.sql`](./06_relative_valuation_multiples.sql)  
**Analytical Objective:** What are the peer valuation multiples across the fintech universe in pure SQL, and how large is UPST's valuation premium?  
**SQL Features:** `Multi-table JOIN between `market_data` and pivot CTE of `financials``  

### SQL Implementation
```sql
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
```

### Query Results (All 9 Rows)

| ticker   |   cal_year |   market_cap_b |   revenue_m |   net_income_m |   equity_m |   ps_multiple |   pb_multiple |   pe_multiple | valuation_tier               |
|:---------|-----------:|---------------:|------------:|---------------:|-----------:|--------------:|--------------:|--------------:|:-----------------------------|
| SOFI     |       2025 |          33.87 |       619.4 |          481.3 |    10489.5 |         54.69 |          3.23 |         70.37 | PREMIUM VALUATION (> 4x P/S) |
| AFRM     |       2025 |          21.96 |      3224.4 |           52.2 |     3069   |          6.81 |          7.15 |        420.73 | PREMIUM VALUATION (> 4x P/S) |
| SEZL     |       2025 |           2.22 |       450.3 |          133.1 |      169.8 |          4.93 |         13.08 |         16.68 | PREMIUM VALUATION (> 4x P/S) |
| UPST     |       2025 |           4.41 |      1043.9 |           53.6 |      798.8 |          4.22 |          5.52 |         82.25 | PREMIUM VALUATION (> 4x P/S) |
| LC       |       2025 |           2.22 |       961.5 |          135.7 |     1500.4 |          2.31 |          1.48 |         16.37 | FAIR / IN-LINE               |
| OMF      |       2025 |           8    |      5455   |          783   |     3401   |          1.47 |          2.35 |         10.22 | FAIR / IN-LINE               |
| PGY      |       2025 |           1.7  |      1301.4 |           81.4 |      480   |          1.31 |          3.55 |         20.93 | FAIR / IN-LINE               |
| ENVA     |       2025 |           3.94 |      3151.7 |          308.4 |     1336.7 |          1.25 |          2.95 |         12.78 | FAIR / IN-LINE               |
| OPRT     |       2025 |           0.24 |       956.7 |           25.2 |      390.1 |          0.25 |          0.61 |          9.35 | DEEP DISCOUNT (< 1x P/S)     |

---

## Query 7: Earnings Decoupling & Operating Cash Burn Audit

**File:** [`sql/07_accruals_earnings_decoupling.sql`](./07_accruals_earnings_decoupling.sql)  
**Analytical Objective:** Which company-years exhibited deceptive accounting health—reporting positive GAAP net income while operating cash flow burned negative?  
**SQL Features:** `Pivot CTE comparing Net Income against CFO and computing non-cash accruals magnitude`  

### SQL Implementation
```sql
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
```

### Query Results (Sample Top 10 Rows)

| ticker   |   cal_year |   net_income_m |   operating_cash_flow_m |   non_cash_accruals_m |   accruals_ratio_tata | earnings_quality_signal          |
|:---------|-----------:|---------------:|------------------------:|----------------------:|----------------------:|:---------------------------------|
| SOFI     |       2022 |         -320.4 |                 -7255.9 |                6935.5 |                 0.365 | CASH BURN / STRUCTURAL LOSS      |
| SOFI     |       2023 |         -300.7 |                 -7227.1 |                6926.4 |                 0.23  | CASH BURN / STRUCTURAL LOSS      |
| SOFI     |       2025 |          481.3 |                 -3742.5 |                4223.8 |                 0.083 | CRITICAL: PROFIT WITH CASH DRAIN |
| LC       |       2025 |          135.7 |                 -2726.9 |                2862.6 |                 0.247 | CRITICAL: PROFIT WITH CASH DRAIN |
| LC       |       2024 |           51.3 |                 -2634.2 |                2685.5 |                 0.253 | CRITICAL: PROFIT WITH CASH DRAIN |
| SOFI     |       2024 |          498.7 |                 -1119.8 |                1618.5 |                 0.045 | CRITICAL: PROFIT WITH CASH DRAIN |
| LC       |       2023 |           38.9 |                 -1136.6 |                1175.5 |                 0.133 | CRITICAL: PROFIT WITH CASH DRAIN |
| SOFI     |       2021 |         -483.9 |                 -1350.2 |                 866.3 |                 0.094 | CASH BURN / STRUCTURAL LOSS      |
| AFRM     |       2026 |         1929.8 |                  1231   |                 698.8 |                 0.044 | NORMAL WORKING CAPITAL ACCRUAL   |
| UPST     |       2022 |         -108.7 |                  -657.9 |                 549.2 |                 0.284 | CASH BURN / STRUCTURAL LOSS      |

---
