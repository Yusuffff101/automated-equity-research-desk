# Methodology Notes: Data Ingestion & Normalization

This document explains the key design decisions made in the data ingestion
pipeline (`ingestion/` module) that are not immediately obvious from the code
alone. It is intended for:

1. **Interviewers** asking "why did you make this choice?"
2. **Future-you** reusing this pipeline for a different sector
3. **Reviewers** assessing the analytical integrity of the project

---

## 1. Why SEC EDGAR Company-Facts API (Not Yahoo Finance / Bloomberg)

The EDGAR `/api/xbrl/companyfacts` endpoint provides every XBRL-tagged
financial fact ever filed by a registrant, going back to the first XBRL
filing. Key advantages for this project:

| Factor | EDGAR | yfinance |
|--------|-------|---------|
| Data source | Direct from the SEC filing | Third-party aggregator (scraping) |
| Historical restated values | Available (multiple filings per period) | Usually only latest revision |
| XBRL tag visibility | Explicit — you can trace every figure to its source | Opaque — you don't know which tag was used |
| Rate limits | 10 req/sec (polite); no API key required | Unofficial; frequently breaks |
| Reproducibility | Fully reproducible from public source | Dependent on a third-party service |

**Caveat**: yfinance is still used for supplementary market data (share price,
market cap) needed for the valuation context in the memo. It is explicitly
**not** used for any fundamental financial data.

---

## 2. XBRL Tag Normalization Strategy

The EDGAR XBRL taxonomy is rich but inconsistent across companies and over time.
Consumer lenders are particularly heterogeneous because:

- **Revenue** is labelled differently depending on business model:
  - BNPL platforms (AFRM, SEZL): mix of merchant fees + interest income →
    `RevenueFromContractWithCustomerExcludingAssessedTax`
  - Traditional lenders (OMF, ENVA, LC): pure interest income →
    `InterestAndFeeIncome` or `InterestAndDividendIncomeOperating`
- **Receivables** (the core earning asset) use 5+ different tag names
  depending on how the company classifies its loan portfolio
- **Gross profit** may simply not exist (no COGS for a lender) → explicit
  `MISSING_TAG` flag, not a silent `NaN`

**Resolution**: A priority-ordered tag mapping in `data/mappings/xbrl_tag_map.json`.
The normalizer tries tags in order and stops at the first match. If no tag
produces annual data, a sentinel row is emitted with `data_quality=MISSING_TAG`.

**This file is inspectable** — you can open `xbrl_tag_map.json` to see
exactly which tags were tried for each company and line item.

---

## 3. Record Deduplication: Why We Keep Only 10-K Records

The EDGAR company-facts JSON for a given balance-sheet date often contains
5–10 records for the same date:

- The original 10-K filing for that period
- Three 10-Q filings in the following fiscal year that carry the prior-year
  comparative figure
- Any 10-K/A amendments

**Decision**: Filter to `form ∈ {10-K, 10-K/A}` and keep the **latest-filed** version.
We distinguish between routine comparative reporting and genuine restatements:
- `COMPARATIVE`: A prior-period value that reappears in a subsequent 10-K with the
  **same** numeric value (standard SEC multi-year comparative disclosure — not an anomaly).
- `RESTATED`: A prior-period value that reappears in a subsequent filing with a
  **different** numeric value than originally reported, or that originates from a
  `10-K/A` amendment.

**Why not keep the original?** Amendments and restatements exist because the original was
inaccurate or revised under new accounting standards — the restated figure is the authoritative one.

---

## 4. Fiscal Year-End Normalization (The AFRM/SEZL Problem)

**Problem**: Two companies in our peer set use a June 30 fiscal year-end:

| Company | Ticker | FYE |
|---------|--------|-----|
| Affirm Holdings | AFRM | June 30 |
| Sezzle Inc. | SEZL | December 31 ✓ |

> **Correction**: After reviewing EDGAR filings, Sezzle uses December 31 FYE.
> Only AFRM has a June 30 FYE in this peer set.

**Decision**: Use the **calendar year of the fiscal period-end date** as the
`cal_year` label for all companies.

| Company | Period End Date | cal_year |
|---------|----------------|---------|
| AFRM | June 30, 2024 | 2024 |
| OMF | December 31, 2024 | 2024 |

**Consequence acknowledged**: When comparing AFRM `cal_year=2024` to OMF
`cal_year=2024`, AFRM's figures reflect the 12-month period July 2023–June 2024,
while OMF's reflect January 2024–December 2024. The periods overlap by 6 months.

**Why accept this?** This is the standard approach used by sell-side analysts
(Bloomberg, FactSet) when comping peers with different FYEs. The alternative —
constructing trailing-twelve-month figures from quarterly data — introduces
additional complexity and potential errors. The FYE difference is documented
explicitly in the dashboard tooltip for AFRM and in the investment memo.

---

## 5. Data Quality Flag System

Every row in the `financials` table carries a `data_quality` column:

| Flag | Meaning | Action for Analyst |
|------|---------|-------------------|
| `OK` | Primary tag found; single filing for this period | Trust the figure |
| `COMPARATIVE` | Prior-period value reported again in a later 10-K with identical value | Routine comparative disclosure; no action needed |
| `FALLBACK_{tag}` | Primary tag absent; fallback used | Verify the fallback tag is semantically equivalent |
| `RESTATED` | Value altered in subsequent filing, or sourced from 10-K/A amendment | Inspect magnitude and footnote disclosure in 10-K/A |
| `ZERO_VALUE` | Tag present but value = 0 | Verify: is 0 legitimate or a filing gap? |
| `MISSING_TAG` | No tag in mapping produced annual data | Row still exists with value=NaN; Phase 3 ratio engine will skip or impute |

**Design principle**: The pipeline never silently drops a company-period.
Every expected (ticker, cal_year, line_item) combination has a row, even
if the value is NaN and the flag is MISSING_TAG. This makes data gaps
visible and auditable.

---

## 6. History Window

The pipeline pulls `MIN_HISTORY_YEARS = 5` years of annual data per company
(configured in `config.py`). This gives us:

- **Dec-FYE companies** (OMF, ENVA, LC, etc.): FY2021, 2022, 2023, 2024, 2025
- **Jun-FYE companies** (AFRM): FY ending Jun 2022, 2023, 2024, 2025, 2026

5 years is the minimum to compute meaningful YoY trends and to calculate
rolling Beneish components (which require at least 2 periods for some variables).

---

## 7. Re-runability

The pipeline is designed to be safe to re-run:

- **Raw cache**: `data/raw/{ticker}.json` is written once and reused.
  Force a fresh pull with `--no-cache`.
- **SQLite**: Uses `INSERT OR REPLACE` with a compound primary key
  `(ticker, cal_year, line_item)` — no duplicate rows on re-run.
- **CSV**: Re-reads the existing file, merges, deduplicates, and rewrites.

Running `python run_ingestion.py --all` twice produces identical output.

---

## 8. Ratio Engine Methodology & Sector Domain Decisions

The Ratio Engine (`ratios/` module) computes 10 standardized financial ratios across 4 categories, tailored to consumer lending and specialty fintech accounting characteristics:

### 1. Profitability Ratios
- **Return on Equity (ROE)**: `net_income / shareholders_equity`.
  - *Distortion guardrail*: If `shareholders_equity < 0` (due to accumulated deficits), ROE flips sign and produces misleading percentages. The engine does not clamp or filter these out; it attaches `DISTORTED_NEGATIVE_EQUITY` to preserve the analytical signal of balance-sheet distress for anomaly detection.
- **Return on Assets (ROA)**: `net_income / total_assets`.
- **Net Margin**: `net_income / revenue`.
- **Gross Margin**: **Explicit N/A** (`"N/A — no COGS concept for lenders"`). Consumer lending business models derive revenue from interest, servicing fees, and gain-on-sale, without Cost of Goods Sold. Attempting to synthesize gross margin creates artificial comparability flaws.

### 2. Leverage Ratios
- **Debt-to-Equity**: `total_debt / shareholders_equity`.
  - Captures total obligations across warehouse facilities, securitization borrowings, and corporate notes. Flagged if equity is negative.
- **Interest Coverage**: `ebit / interest_expense`.
  - *Synthetic EBIT Architecture*: Pure lenders and bank holding companies (`SOFI`, `LC`, `OMF`, `OPRT`) do not classify `OperatingIncomeLoss` on their income statement. For these filers, the engine calculates **Synthetic EBIT**:
    $$\text{Synthetic EBIT} = \text{NetIncomeLoss} + \text{IncomeTaxExpenseBenefit} + \text{InterestExpense}$$
  - The ratio is tagged with `SYNTHETIC_EBIT` to maintain strict auditability.

### 3. Liquidity Ratios
- **Current Ratio & Quick Ratio**: **Explicit N/A** (`"N/A — lenders don't classify current/non-current assets"`). Financial institutions do not present classified balance sheets (no current/non-current distinction for loan portfolios). Outputting explicit N/A strings prevents erroneous ratio computation from partial tag matches.

### 4. Efficiency Ratios
- **Asset Turnover**: `revenue / total_assets`.
- **Receivables Turnover**: `revenue / receivables`.
  - *Securitization / Fair Value Exception*: For Pagaya (`PGY`) and Enova (`ENVA`), loans are either securitized off-balance-sheet via ABS vehicles or carried under ASC 825 Fair Value Option. Standard receivables turnover is structurally meaningless and is assigned **Explicit N/A** (`"N/A — securitized/fair-value receivables structure"`).

### 5. Zero-Division & Traceability Guardrails
- **Zero Denominators**: Division by zero is never executed silently; any zero or missing denominator outputs a descriptive reason string (e.g., `"N/A — zero equity"`).
- **Quality Inheritance**: Ratios inherit the data-quality flags of their underlying line items (e.g., `RESTATED`, `FALLBACK`, `SYNTHETIC_EBIT`), enabling downstream modules to identify which ratios are based on restated filings.

---

## 9. Anomaly & Red-Flag Detection Module Methodology

The Anomaly & Red-Flag Detection Module (`anomaly/` module) evaluates financial health, earnings manipulation risk, and credit-growth divergence across the 9 public fintech and specialty lender peers. 

Because classical forensic accounting models (Beneish M-Score and Altman Z-Score) were calibrated on manufacturing/non-financial corporations, direct application to financial institutions produces distorted results. This section details the explicit domain adaptations applied.

### 1. Adapted Beneish M-Score (ex-GMI, Financial Institution Adjustment)

The classical 8-variable Beneish M-Score formula is:
$$M = -4.84 + 0.920 \cdot \text{DSRI} + 0.528 \cdot \text{GMI} + 0.404 \cdot \text{AQI} + 0.892 \cdot \text{SGI} + 0.115 \cdot \text{DEPI} - 0.172 \cdot \text{SGAI} + 4.037 \cdot \text{TATA} + 0.0327 \cdot \text{LVGI}$$

#### Why Standard Beneish Fails for Lenders:
- **Gross Margin Index (GMI)**: Requires Gross Margin $= (\text{Revenue} - \text{COGS}) / \text{Revenue}$. As established in Phase 3, consumer lenders have no Cost of Goods Sold concept; revenues are derived from interest margins, gain-on-sale, and origination/servicing fees. Forcing GMI computation yields missing values or invalid divisions.

#### Adaptation & Calibration Decisions:
1. **Exclude GMI**: The $+0.528 \cdot \text{GMI}$ term is dropped from the regression equation. The intercept is adjusted to $-4.493$ (reflecting the neutral baseline where excluded indices equal $1.0$).
2. **Neutralize Manufacturing Indices**: Depreciation Index (DEPI), Asset Quality Index (AQI), and SG&A Index (SGAI) are structurally unobserved or distorted in pure loan portfolios and default to $1.0$ (neutral).
3. **Adapted Formula**:
   $$M_{\text{adapted}} = -4.493 + 0.920 \cdot \text{DSRI} + 0.892 \cdot \text{SGI} + 4.037 \cdot \text{TATA} + 0.0327 \cdot \text{LVGI}$$
   Where:
   - $\text{DSRI} = (\text{Receivables}_t / \text{Revenue}_t) / (\text{Receivables}_{t-1} / \text{Revenue}_{t-1})$
   - $\text{SGI} = \text{Revenue}_t / \text{Revenue}_{t-1}$
   - $\text{TATA} = (\text{Net Income}_t - \text{Operating Cash Flow}_t) / \text{Total Assets}_t$
   - $\text{LVGI} = (\text{Total Debt}_t / \text{Total Assets}_t) / (\text{Total Debt}_{t-1} / \text{Total Assets}_{t-1})$
4. **Receivables Domain Exception**: For Pagaya (`PGY`) and Enova (`ENVA`), loan assets are securitized off-balance-sheet via ABS trusts or held under ASC 825 Fair Value Option. For these filers, $\text{DSRI}$ is neutralized to $1.0$ with an explicit explanatory note.
5. **Directional Interpretation**: The standard Beneish cutoff of $-1.78$ was calibrated including GMI on non-financial firms. The adapted M-Score is labeled as `"Adapted M-Score (ex-GMI, financial institution adjustment)"` and interpreted directionally (comparative ranking of aggressive accruals and revenue expansion) rather than as a strict binary pass/fail verdict. Scores $> -1.78$ indicate elevated risk relative to peers.

### 2. Adapted Altman Z-Score (Cash/TA Liquidity Substitution)

The classical Altman Z-Score formula is:
$$Z = 1.2 \cdot X_1 + 1.4 \cdot X_2 + 3.3 \cdot X_3 + 0.6 \cdot X_4 + 0.999 \cdot X_5$$

#### Why Standard Altman Z Fails for Lenders:
- **$X_1 = \text{Working Capital} / \text{Total Assets}$**: Working Capital requires Current Assets minus Current Liabilities. Financial institutions do not present classified balance sheets; loan assets and warehouse borrowings are not segregated into current vs. non-current buckets.
- **$X_4 = \text{Market Value of Equity} / \text{Total Liabilities}$**: Requires historical daily share price and shares outstanding as of the fiscal period-end date, which is absent from raw SEC XBRL financial statements.

#### Adaptation & Calibration Decisions:
1. **Cash & Cash Equivalents Substitution for $X_1$**:
   $$\text{Adapted } X_1 = \frac{\text{Cash \& Cash Equivalents}}{\text{Total Assets}}$$
   - *Rationale*: Cash & cash equivalents is universally disclosed across all 9 filers and represents the truest immediate liquidity buffer available to absorb credit losses, collateral calls, or warehouse haircuts. Because $\text{Cash} \le \text{Working Capital}$, this substitution provides a conservative liquidity assessment.
2. **Synthetic EBIT for $X_3$**: For bank holding companies and fintech lenders lacking direct `OperatingIncomeLoss` (`SOFI`, `LC`, `OMF`, `OPRT`), the Phase 3 Synthetic EBIT ($\text{Net Income} + \text{Tax} + \text{Interest Expense}$) is utilized.
3. **Market Equity Ingestion ($X_4$)**:
   $$\text{MVE} = \text{Fiscal Year-End Closing Share Price} \times \text{Diluted Shares Outstanding}$$
   Historical market capitalization is ingested via `yfinance` as of each fiscal period-end and stored in SQLite `market_data` and `data/normalized/market_data.csv`.
4. **Pre-IPO Graceful Handling**: For companies that completed IPOs or SPAC mergers during the coverage period (`SEZL` pre-2023, `AFRM` FY2020, `SOFI` 2020, `PGY` 2020), market value is unavailable. The score is assigned `"N/A — Pre-IPO (MVE unavailable)"` with flag `PRE_IPO_UNAVAILABLE`. The pipeline **never fabricates** private valuations or substitutes zero market cap.
5. **Zone Thresholds**:
   - **Distress Zone**: $Z < 1.81$
   - **Grey Zone**: $1.81 \le Z \le 2.99$
   - **Safe Zone**: $Z > 2.99$

### 3. Balance-Sheet Accruals Ratio

Measures the proportion of accounting net income not backed by cash from operations:
$$\text{Accruals Ratio} = \frac{\text{Net Income} - \text{Operating Cash Flow}}{\text{Total Assets}}$$

#### Sector Interpretation:
In consumer credit, persistent high positive accruals ($> +10\%$) frequently indicate uncollected accrued interest, delayed loan loss provisioning, or mark-to-model gains on retained ABS tranches. Conversely, large negative accruals ($< -10\%$) demonstrate strong cash conversion exceeding reported GAAP earnings.

### 4. Revenue vs. Receivables Growth Divergence

Computes the spread between annual receivables expansion and topline revenue growth:
$$\text{Growth Divergence} = \text{YoY Receivables Growth} - \text{YoY Revenue Growth}$$

#### Sector Domain Rules & Exemption:
- **Red Flag Threshold**: When receivables growth outpaces revenue growth by $> 15\%$, it signals potential credit loosening, aggressive loan volume booking, or delayed non-accrual reclassifications.
- **Structural Exemption for PGY and ENVA**: Pagaya (`PGY`) operates an off-balance-sheet partner network where loans are transferred immediately into securitization vehicles. Enova (`ENVA`) designates consumer loans under the ASC 825 Fair Value Option. For both companies, on-balance-sheet receivables growth is structurally inapplicable and is assigned **Explicit N/A** (`"N/A — securitized/fair-value receivables structure"`).

### 5. Cross-Correlation with Phase 3 Outlier Signals

The 17 distress outliers identified during the Phase 3 audit serve as a cross-model validation benchmark:
1. **Affirm (AFRM)**: Persistent negative interest coverage from FY2022 to FY2025 directly coincides with Adapted Z-Scores in the **Distress Zone** ($Z = 0.43, -0.12, 0.53, 1.65$).
2. **Oportun Financial (OPRT)**: Subprime credit losses and near-zero/negative interest coverage in 2022–2023 map to severe Altman Z **Distress Zone** placements ($Z = 0.35, 0.23$).
3. **Pagaya Technologies (PGY)**: The FY2024 10-K/A restatement and $-123\%$ ROE shock drive an Altman Z-Score of $0.66$ (**Distress Zone**), driven by an accumulated deficit of $\$-944\text{M}$ and $\$-401.4\text{M}$ net loss.
4. **Upstart Holdings (UPST)**: The 2022–2023 interest rate shock and negative coverage ($-10.5\text{x}, -7.35\text{x}$) place UPST squarely into the **Distress Zone** ($Z = 0.72, 1.39$).
5. **Sezzle (SEZL)**: Early venture-stage negative equity and operating losses in 2021–2022 are correctly quarantined as `PRE_IPO_UNAVAILABLE` in Altman Z while Accruals Ratios capture the rapid cash-burn trajectory before its 2023–2024 turnaround.

