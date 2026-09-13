# 📊 Automated Equity Research Desk

[![Python 3.11](https://img.shields.io/badge/python-3.11.5-blue.svg)](https://www.python.org/downloads/release/python-3115/)
[![SEC EDGAR](https://img.shields.io/badge/data-SEC%20EDGAR%20(100%25%20Real)-green.svg)](https://www.sec.gov/edgar)
[![Streamlit Cloud](https://img.shields.io/badge/dashboard-Streamlit%20Cloud-FF4B4B.svg)](https://automated-equity-research-desk.streamlit.app/)
[![Research Memo](https://img.shields.io/badge/memo-2--Page%20PDF-purple.svg)](memo/UPST_investment_memo.pdf)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, institutional equity research workstation that autonomously harvests SEC EDGAR filings, computes sector-adapted financial ratios, detects forensic accounting red flags, and renders a 2-page investment memo backed by interactive terminal analytics.

---

## ⚡ 30-Second Overview (Why This Isn't a Kaggle Dashboard)

Most financial dashboards plot clean, pre-packaged CSVs from Kaggle or Yahoo Finance, computing textbook ratios that silently fail when applied to real companies. In the real world:
- **Lenders have no Cost of Goods Sold (COGS)**: Standard gross margins are meaningless for fintech lenders, yet generic dashboards display them without question.
- **Financial institutions lack classified balance sheets**: Current Assets and Current Liabilities are omitted from financial institution 10-Ks, breaking textbook Altman Z-Score and Beneish M-Score models.
- **SEC disclosures are noisy and restated**: A prior period figure may be restated in a 10-K/A amendment or presented comparatively under different accounting standards (e.g., CECL provisioning or Fair Value Option shifts).

**This desk solves those problems.** It pulls 100% real XBRL company facts directly from the SEC EDGAR API across 9 public fintech and consumer lending peers (`AFRM`, `SEZL`, `UPST`, `SOFI`, `LC`, `PGY`, `OPRT`, `OMF`, `ENVA`) from FY2021 to FY2026. It applies mathematically adapted forensic models, surfaces genuine earnings-quality red flags, and publishes an institutional 2-page investment memo with an explicit, evidence-backed rating.

---

## 🏛️ Architecture & Approach

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AUTOMATED RESEARCH DESK PIPELINE                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│  SEC EDGAR API   │ ───► │   XBRL Normalizer      │ ───► │  Tidy Data Store       │
│  (Company Facts) │      │  • Tag Fallback Maps   │      │  • SQLite (Primary DB) │
│  9 Public CIKs   │      │  • 10-K/A Restatements │      │  • CSV (Web Portability)│
└──────────────────┘      │  • Calendar-Year Align │      └────────────────────────┘
                          └────────────────────────┘                   │
                                                                       ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               ANALYTICAL ENGINES                                  │
├─────────────────────────────────────────┬─────────────────────────────────────────┤
│          FINANCIAL RATIO ENGINE         │     ADAPTED FORENSIC ANOMALY MODULE     │
│  • Profitability: ROE, ROA, Net Margin  │  • Adapted Beneish M-Score (ex-GMI)     │
│  • Leverage: Debt-to-Equity, Coverage   │  • Adapted Altman Z-Score (Cash/TA)     │
│  • Efficiency: Asset & Rec Turnover     │  • Accruals Ratio (TATA: NI vs. CFO)    │
│  • Domain Guardrail: Explicit COGS N/A  │  • Growth Divergence (Rev vs. Rec)      │
└─────────────────────────────────────────┴─────────────────────────────────────────┘
         │                                                             │
         ▼                                                             ▼
┌─────────────────────────────────────────┐       ┌─────────────────────────────────────────┐
│     INTERACTIVE STREAMLIT TERMINAL      │       │     INSTITUTIONAL INVESTMENT MEMO       │
│  • Side-by-Side Peer Trajectories       │       │  • Strictly 2-Page Institutional Note   │
│  • Extreme Outlier Axis Bounding        │       │  • UPST Initiation: AVOID / HIGH RISK   │
│  • Explicit Visual Pre-IPO/Missing N/A  │       │  • Step 0 Longitudinal Trajectory Audit │
│  • Executive Threat Matrix & Popovers   │       │  • Relative Multiples vs. 8 Peers       │
└─────────────────────────────────────────┘       └─────────────────────────────────────────┘
```

### Why BNPL & Technology-Driven Specialty Lenders?
We deliberately chose a sub-sector characterized by acute accounting complexity and credit-cycle volatility:
1. **Originate-to-Distribute vs. Balance-Sheet Retention**: Companies like Upstart (`UPST`) and Pagaya (`PGY`) claim to be capital-light AI marketplaces, but interest rate shocks can instantly trap loans on their balance sheets.
2. **Accounting Method Shifts**: Frequent transitions between Fair Value Option (FVO) accounting, CECL loss reserves, and securitization warehouse debt obscure true operating performance.
3. **High Anomaly Density**: This sector produces authentic distress and earnings-quality signals—providing a rigorous proving ground for forensic algorithms.

| Ticker | Company | CIK | Core Business Model & Accounting Nuance |
|:-------|:--------|:---:|:----------------------------------------|
| **AFRM** | Affirm Holdings | 0001820953 | Pure-play BNPL; gain-on-sale accounting; June FYE normalized to calendar year. |
| **SEZL** | Sezzle Inc. | 0001662991 | High-velocity BNPL; recent GAAP profitability; clean low-risk benchmark. |
| **UPST** | Upstart Holdings | 0001647639 | AI lending marketplace; 2022 loan inventory blowup and 2025 cash flow relapse. |
| **SOFI** | SoFi Technologies | 0001818874 | Diversified fintech with national bank charter; large CECL provisioning. |
| **LC** | LendingClub Corp | 0001409970 | Marketplace pioneer turned digital bank; deposit-funded consumer credit. |
| **PGY** | Pagaya Technologies | 0001883085 | AI securitization network; SEC 10-K/A restatement and severe Altman Z distress. |
| **OPRT** | Oportun Financial | 0001538716 | Subprime lender; structural credit deterioration and debt renegotiation. |
| **OMF** | OneMain Holdings | 0001584207 | Legacy branch/digital installment lender; mature high-yield comp anchor. |
| **ENVA** | Enova International | 0001529864 | Online non-prime lender; extensive Fair Value Option (FVO) portfolio election. |

---

## 🔍 Headline Forensic Discoveries

### 1. Pagaya Technologies (`PGY`): 10-K/A Restatement Coinciding with Altman Z Distress
- In FY2023, Pagaya filed a formal **10-K/A amendment** restating previously reported net income and equity values.
- Our pipeline flagged PGY's restatement simultaneously with an **Adapted Altman Z-Score of 1.39 (deep in the Distress Zone < 1.81)**.
- While PGY improved to Grey Zone ($Z = 1.87$) in FY2025, it maintains thin tangible equity ($480M) supporting over $1.3B in securitization liabilities.

### 2. Enova International (`ENVA`): Fair Value Option (FVO) Masking Credit Loss Volatility
- Enova shifted significant portions of its subprime loan portfolio to **Fair Value Option (FVO) accounting** under ASC 825.
- Because FVO folds credit loss adjustments directly into "Change in Fair Value" rather than a discrete provision expense, standard credit allowance ratios show `MISSING_TAG`.
- Our pipeline correctly isolated ENVA's structural high-charge-off model and tracked its equity multiple discount (12.8x P/E vs. peer median of 16.7x).

### 3. Upstart Holdings (`UPST`): The 2025 "Turnaround" Is Bifurcated & Incomplete
Prior to drafting the investment memo, Step 0 audited Upstart's full 2021–2025 trajectory:
- **The Bull Case Narrative**: Revenue surged +64.0% YoY to $1,043.9M, and reported GAAP Net Income inflected to $+53.6M (ROE +6.71%).
- **The Balance Sheet Reality**:
  - Operating cash flow relapsed to **$-147.7M** (generating $+201.3M in non-cash accruals).
  - Total debt climbed to an all-time peak of **$1.39B**.
  - Cash liquidity dropped from $788M to $652M.
  - The **Adapted Altman Z-Score fell back into the Distress Zone at 1.71 (< 1.81)**.

### 4. Upstart Investment Thesis: AVOID / HIGH RISK (Valuation Stretch)
- **Priced for AI Perfection**: UPST trades at **82.25x P/E** (nearly **5x the profitable peer median of 16.68x**), **4.22x P/S** (+83% premium), and **5.52x P/B** (+71% premium).
- **The Mismatch**: Investors are paying an elite software multiple for a business sitting in the Altman Z Distress Zone with negative cash generation. If originations slow or warehouse lines tighten, UPST faces **60%–75% downside multiple re-rating risk**.

---

## 📈 Relative Valuation Benchmark (FY2025 Multiples)

*Computed from live market capitalization data against normalized SEC EDGAR financials (no DCF per PRD scope):*

| Ticker | Company Name | Market Cap ($B) | Revenue ($M) | Net Income ($M) | Shareholders' Equity ($M) | P/S | P/B | P/E | Solvency Risk Profile |
|:-------|:-------------|:---------------:|:------------:|:---------------:|:-------------------------:|:---:|:---:|:---:|:----------------------|
| **AFRM** | Affirm Holdings | $21.96B | $3,224.4M | $+52.2M | $3,069.0M | 6.81x | 7.15x | 420.7x | Distress Zone ($Z = 1.65$) |
| **ENVA** | Enova International | $3.94B | $3,151.7M | $+308.4M | $1,336.7M | 1.25x | 2.95x | 12.8x | Distress Zone ($Z = 1.62$) |
| **LC**   | LendingClub | $2.22B | $961.5M | $+135.7M | $1,500.4M | 2.31x | 1.48x | 16.4x | Distress Zone ($Z = 0.34$) |
| **OMF**  | OneMain Holdings | $8.00B | $5,455.0M | $+783.0M | $3,401.0M | 1.47x | 2.35x | 10.2x | Distress Zone ($Z = 0.84$) |
| **OPRT** | Oportun Financial | $0.24B | $956.7M | $+25.2M | $390.1M | 0.25x | 0.61x | 9.4x | Distress Zone ($Z = 0.56$) |
| **PGY**  | Pagaya Technologies | $1.70B | $1,301.4M | $+81.4M | $480.0M | 1.31x | 3.55x | 20.9x | Grey Zone ($Z = 1.87$) |
| **SEZL** | Sezzle Inc. | $2.22B | $450.3M | $+133.1M | $169.8M | 4.93x | 13.08x | 16.7x | **Safe Zone ($Z = 8.55$)** |
| **SOFI** | SoFi Technologies | $33.87B | $619.4M | $+481.3M | $10,489.5M | 54.69x | 3.23x | 70.4x | Distress Zone ($Z = 0.65$) |
| **UPST** | **Upstart Holdings** | **$4.41B** | **$1,043.9M** | **$+53.6M** | **$798.8M** | **4.22x** | **5.52x** | **82.25x** | **Distress Zone ($Z = 1.71$)** |
| **MEDIAN**| **Peer Group Median** | **$2.22B** | **$1,043.9M** | **$+133.1M** | **$1,336.7M** | **2.31x** | **3.23x** | **16.68x** | — |

---

## 🔗 Live Links & Artifacts

- **Live Streamlit Dashboard**: [https://automated-equity-research-desk.streamlit.app/](https://automated-equity-research-desk.streamlit.app/) *(or local `http://localhost:8501`)*
- **UPST Investment Memo (PDF)**: [`memo/UPST_investment_memo.pdf`](memo/UPST_investment_memo.pdf) *(Strict 2-Page Institutional Note)*
- **UPST Investment Memo (Markdown)**: [`memo/UPST_investment_memo.md`](memo/UPST_investment_memo.md)
- **Spoken Walkthrough Script**: [`memo/walkthrough_script.md`](memo/walkthrough_script.md)
- **Methodology & Model Adaptations**: [`METHODOLOGY.md`](METHODOLOGY.md)

---

## 🚀 How to Run (Single-Command Reproducibility)

### 1. Prerequisites & Installation
```bash
# Clone the repository
git clone https://github.com/Yusuffff101/automated-equity-research-desk.git
cd automated-equity-research-desk

# Create and activate Python virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Single-Command End-to-End Pipeline
Run the entire analytical pipeline—from EDGAR normalization to ratio calculation, anomaly detection, and 2-page PDF memo generation:
```bash
python run_pipeline.py
```
*Executes in under 6 seconds using local SEC cache!*

### 3. Launch the Interactive Dashboard
```bash
streamlit run dashboard/app.py
```
Open `http://localhost:8501` in your browser to explore the institutional terminal.

---

## 🛡️ Data Authenticity Notice

**All financial data in this repository is 100% authentic, unsimulated SEC EDGAR XBRL company facts.**
- Harvested directly from SEC EDGAR's `/api/xbrl/companyfacts/` endpoint adhering to official SEC rate limits and declared User-Agent identification.
- Covers 9 public reporting entities across 6 fiscal years (FY2021–FY2026).
- Every tag, comparative value, and amendment is tracked with audit-trail provenance (`data_quality` flags: `OK`, `COMPARATIVE`, `FALLBACK`, `MISSING_TAG`, `RESTATED`).

---

## 🔭 Future Work & Intentional Scope Boundaries

Per PRD section 1.2, several items were intentionally bounded to maintain high signal-to-noise on core earnings quality:
1. **Intraday Streaming Data**: Fundamental equity research evaluates multi-year annual 10-K filings. High-frequency price feeds add latency without improving accounting red-flag detection.
2. **Discounted Cash Flow (DCF) Modeling**: DCF models assume a distinct reinvestment rate and free cash flow to firm ($FCFF$). For balance-sheet lenders whose primary raw material is borrowed capital, DCFs produce meaningless enterprise values. Multiples and credit solvency models are the domain standard.
3. **Multi-Sector Coverage**: The XBRL fallback maps and adapted Beneish/Altman formulas are specifically tailored to financial institutions and specialty lenders. Generalizing across non-financial manufacturing would dilute sector-specific forensic precision.
