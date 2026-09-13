# 📘 Data Dictionary: Tableau Public BI Export Layer

**File:** [`data/exports/tableau_export.csv`](./tableau_export.csv)  
**Dataset Grain:** 1 row per Company-Year (`Ticker` × `Calendar_Year`)  
**Dimensions:** 54 rows (9 public companies × 6 calendar years: 2021–2026) × 47 columns  
**Primary Key:** `(Ticker, Calendar_Year)`  
**Target BI Application:** Tableau Public / Tableau Desktop / Power BI  
**Author:** Automated Equity Research Desk  

---

## 1. Company Metadata & Identifiers

| Column Name | Data Type | Description | Example Values |
|:---|:---:|:---|:---|
| `Ticker` | String | Public stock ticker symbol traded on US exchanges | `UPST`, `AFRM`, `SOFI`, `SEZL` |
| `Company_Name` | String | Full legal corporate entity name registered with SEC | `Upstart Holdings, Inc.`, `Affirm Holdings, Inc.` |
| `CIK` | String (10-char) | Central Index Key assigned by SEC EDGAR | `0001647639`, `0001820953` |
| `Subsector` | String | Business model classification within specialty credit | `AI Marketplace Lending`, `Buy Now Pay Later (BNPL)` |
| `Calendar_Year` | Integer | Normalized calendar reporting year (Jan 1 – Dec 31) | `2021`, `2022`, `2023`, `2024`, `2025`, `2026` |
| `Fiscal_Period_End` | Date (YYYY-MM-DD)| Actual period-end balance sheet date of annual filing | `2025-12-31`, `2025-06-30` (AFRM/SEZL) |

> **Fiscal Year Normalization Caveat:** Affirm (`AFRM`) and Sezzle (`SEZL`) operate on June fiscal year-ends. Per [`METHODOLOGY.md`](../../METHODOLOGY.md), their fiscal years are aligned to nearest calendar years (e.g., June 2025 FYE maps to Calendar Year 2025) to preserve cross-sectional comparability.

---

## 2. Fundamental Financial Statement Line Items ($ Millions)

*All values expressed in millions of USD ($M), rounded to 2 decimal places.*

| Column Name | Data Type | SEC Line Item Definition | Sector Interpretation / Caveats |
|:---|:---:|:---|:---|
| `Revenue_M` | Float | Total net revenues from contracts, fees, interest | Total top-line platform revenue |
| `Net_Income_M` | Float | GAAP Net Income / Loss attributable to common shareholders | Bottom-line accounting profit after tax and credit charges |
| `Operating_Cash_Flow_M`| Float | Cash flow generated from operating activities (CFO) | Cash conversion measure; critical for accruals audit |
| `Total_Assets_M` | Float | Total balance-sheet assets | Foundation for ROA and Altman Z scaling |
| `Total_Liabilities_M` | Float | Total balance-sheet obligations | Debt + warehouse lines + customer payables |
| `Shareholders_Equity_M`| Float | Total stockholders' equity buffer | Net book value; denominator for ROE and Debt/Equity |
| `Total_Debt_M` | Float | Sum of long-term debt, short-term debt, and warehouse lines | Captures off-balance-sheet & securitization credit facilities |
| `Cash_And_Equivalents_M`| Float | Unrestricted cash, cash equivalents, and short-term deposits | Primary liquidity buffer; replaces Working Capital in Altman Z |
| `EBIT_M` | Float | Operating Income or Synthetic EBIT (`Net Income + Tax + Interest`)| Operating earning power before financing costs |
| `Interest_Expense_M` | Float | Total interest and financing fees incurred | Denominator for interest coverage |
| `Receivables_M` | Float | Net loans, leases, and financing receivables | Loans held for investment/sale; driver of divergence flags |
| `Retained_Earnings_M` | Float | Cumulative retained earnings or accumulated deficit | Solvency drag term $X_2$ in Altman Z-Score |

---

## 3. Financial & Credit Leverage Ratios

| Column Name | Data Type | Formula | Sector Interpretation / Benchmarks |
|:---|:---:|:---|:---|
| `ROE_Pct` | Float (%) | `(Net Income / Shareholders' Equity) * 100` | Return on Equity. Outliers clipped in dashboard view |
| `ROA_Pct` | Float (%) | `(Net Income / Total Assets) * 100` | Return on Assets; reflects balance sheet asset profitability |
| `Net_Margin_Pct` | Float (%) | `(Net Income / Revenue) * 100` | Net margin percentage |
| `Debt_To_Equity_Mult` | Float (x) | `Total Debt / Shareholders' Equity` | Leverage multiple; values > 4.0x indicate thin equity buffer |
| `Interest_Coverage_Mult`| Float (x) | `EBIT / Interest Expense` | Safety buffer; values < 1.5x indicate elevated credit risk |
| `Asset_Turnover_Mult` | Float (x) | `Revenue / Total Assets` | Platform revenue velocity per dollar of assets |
| `Receivables_Turnover_Mult`| Float (x) | `Revenue / Receivables` | Turnover speed of loans held on balance sheet |

> **Gross Margin Note:** Gross margin is intentionally omitted (`N/A`) across the entire universe because financial lenders have no Cost of Goods Sold (COGS). Displaying gross margin for lenders is analytically erroneous per PRD §4.2.

---

## 4. Sector-Adapted Forensic Anomaly Models

| Column Name | Data Type | Formula & Thresholds | Analytical Purpose & Tooltip Copy |
|:---|:---:|:---|:---|
| `Adapted_Altman_Z_Score` | Float | $1.2(Cash/TA) + 1.4(RE/TA) + 3.3(EBIT/TA) + 0.6(MVE/TL) + 1.0(Sales/TA)$ | Solvency score. Safe (> 2.99), Grey (1.81–2.99), Distress (< 1.81) |
| `Altman_Z_Classification`| String | `DISTRESS_ZONE`, `GREY_ZONE`, `SAFE_ZONE`, `PRE_IPO_UNAVAILABLE` | Categorical risk zone for color mapping in Tableau |
| `Altman_Z_Methodology` | String | Fixed disclosure string | *"Adapted Z-Score (Cash/TA substitution for unclassified balance sheets)"* |
| `Adapted_Beneish_M_Score`| Float | 7-variable adapted equation (Gross Margin Index excluded) | Manipulation index. Safe (< -1.78), Elevated Risk (> -1.78) |
| `Beneish_M_Classification`| String | `LOW_MANIPULATION_RISK`, `ELEVATED_MANIPULATION_RISK` | Categorical earnings risk tier |
| `Beneish_M_Methodology` | String | Fixed disclosure string | *"Adapted M-Score (ex-GMI financial institution adjustment)"* |
| `Accruals_Ratio` | Float | `(Net Income - Operating Cash Flow) / Total Assets` | Sloan Accruals. Normal (<= 0.05), Decoupled / Flag (> 0.05) |
| `Accruals_Classification`| String | `NORMAL`, `HIGH_ACCRUALS_DIVERGENCE` | Identifies where accounting profit is unbacked by cash |
| `Growth_Divergence_Pct` | Float (%) | `YoY Receivables Growth % - YoY Revenue Growth %` | Flag if spread > +30.0% (loans piling up on balance sheet) |
| `Growth_Divergence_Classification`| String | `NORMAL`, `FLAG_GROWTH_DIVERGENCE`, `INVENTORY_OFFLOAD` | Inventory shock detection flag |

---

## 5. Market Valuation & Enterprise Multiples

| Column Name | Data Type | Source / Formula | Analytical Purpose |
|:---|:---:|:---|:---|
| `Close_Price` | Float ($) | Year-end closing stock price from secondary market | Benchmark equity price |
| `Shares_Outstanding_M` | Float | Diluted weighted shares outstanding (Millions) | Equity denominator |
| `Market_Cap_M` | Float ($M) | `Close Price * Shares Outstanding` | Total equity market capitalization |
| `PS_Multiple` | Float (x) | `Market Cap / Revenue` | Price-to-Sales multiple |
| `PB_Multiple` | Float (x) | `Market Cap / Shareholders' Equity` | Price-to-Book multiple |
| `PE_Multiple` | Float (x) | `Market Cap / Net Income` (Positive Net Income only) | Price-to-Earnings multiple (null for loss-making periods) |
| `Is_Pre_IPO` | Integer (0/1)| 1 if company was private during reporting year; 0 if public | Filter for Tableau to avoid plotting synthetic zeroes |

---

## 6. Data Quality & Audit-Trail Provenance

| Column Name | Data Type | Description | Intended Tableau Use |
|:---|:---:|:---|:---|
| `Restated_Fact_Count` | Integer | Number of financial line items sourced from 10-K/A amendments | Marks restatement risk (e.g. Pagaya 2023 restatements) |
| `Comparative_Fact_Count`| Integer | Number of prior-period comparative disclosures | Distinguishes routine recast from material restatements |
| `Missing_Tag_Count` | Integer | Number of required tags missing in SEC XBRL taxonomy | Identifies disclosure non-conformance |
| `Data_Quality_Summary` | String | Concise human-readable provenance summary | Tooltip copy (e.g. *"24 facts restated (10-K/A); 38 missing tags"*) |

---

## 7. Recommended Tableau Visualizations

1. **Valuation Multiple vs. Solvency Scatterplot**:
   - **X-Axis**: `Adapted_Altman_Z_Score` (Reference line at $Z = 1.81$)
   - **Y-Axis**: `PE_Multiple` or `PS_Multiple` (Log scale recommended)
   - **Color**: `Altman_Z_Classification` (Red = Distress, Yellow = Grey, Green = Safe)
   - **Size**: `Market_Cap_M`
   - *Reveals UPST's extreme valuation premium while sitting in the Distress Zone.*

2. **Forensic Accruals Decoupling Bar Chart**:
   - **Dimension**: `Ticker` (Filtered to 2025)
   - **Measures**: `Net_Income_M` vs. `Operating_Cash_Flow_M`
   - *Visually proves Upstart's negative cash conversion despite positive net income.*

3. **Receivables vs. Revenue Growth Divergence Time Series**:
   - **Dual Axis**: `Revenue_M` (Bars) vs. `Receivables_M` (Lines) across `Calendar_Year`
   - *Highlights the 2022 loan inventory blowup.*
