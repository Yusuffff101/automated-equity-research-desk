# 📊 Automated Equity Research Desk

[![Python 3.11](https://img.shields.io/badge/python-3.11.5-blue.svg)](https://www.python.org/downloads/release/python-3115/)
[![SEC EDGAR](https://img.shields.io/badge/data-SEC%20EDGAR%20(100%25%20Real)-green.svg)](https://www.sec.gov/edgar)
[![Streamlit Cloud](https://img.shields.io/badge/dashboard-Streamlit%20Cloud-FF4B4B.svg)](https://automated-equity-research-desk.streamlit.app/)
[![Research Memo](https://img.shields.io/badge/memo-2--Page%20PDF-purple.svg)](memo/UPST_investment_memo.pdf)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A 9-company forensic financial analysis pipeline built on real SEC filings — data ingestion, anomaly detection, an interactive dashboard, and a defensible investment recommendation, end to end.

🔗 **[Live Dashboard](https://automated-equity-research-desk.streamlit.app/)** · **[Tableau Public Dashboard](#)** · **[Investment Memo (PDF)](memo/UPST_investment_memo.pdf)** · **[SQL Query Showcase](sql/README.md)** · **[Methodology](METHODOLOGY.md)**

---

## The Problem

Most "financial analysis" portfolio projects stop at a ratio dashboard built from a static, pre-cleaned CSV — which shows spreadsheet literacy, not analytical judgment. This project instead builds a full pipeline that pulls real, messy, inconsistently-tagged data directly from source (SEC EDGAR's API, not Kaggle), does the mechanical work of cleaning and normalizing it, flags genuine anomalies through statistical and forensic modeling, and produces a real, numbers-backed investment call — the way an actual research desk would.

It's a finance use case, but the underlying skills are general-purpose analytics work: sourcing and normalizing inconsistent real-world data, building a data-quality/provenance layer, detecting anomalies when standard models don't fit the data as-is, and communicating findings clearly enough for someone to act on.

---

## Approach

- **Universe Selection**: 9 comparable public companies in BNPL and consumer/specialty lending fintech (`AFRM`, `SEZL`, `UPST`, `SOFI`, `LC`, `PGY`, `OPRT`, `OMF`, `ENVA`) — chosen specifically because this sub-sector has real accounting complexity (fair-value loan accounting, securitization, CECL provisioning) and a genuine history of red flags, rather than a "clean" sector where nothing interesting would surface.
- **SEC EDGAR API Ingestion**: Data ingestion directly from SEC EDGAR's XBRL company-facts API, with a custom tag-mapping layer to reconcile inconsistent tagging across companies (e.g., lenders use different tags for debt, receivables, and interest expense depending on their funding structure).
- **Data Quality & Provenance Layer**: A full data-quality/provenance system — every financial fact is tagged `OK`, `COMPARATIVE`, `RESTATED`, `FALLBACK`, `MISSING_TAG`, or `NOT_APPLICABLE`, so every downstream number is traceable back to how confidently it was sourced. This surfaced genuine findings on its own — see below.
- **Financial Ratio Engine**: A ratio engine (profitability, leverage, liquidity, efficiency) with explicit guardrails: no silent division-by-zero, no fabricated ratios for line items a lender's business model doesn't have (e.g., gross margin, current ratio).
- **Adapted Forensic Anomaly Detection**: An anomaly/forensic module using Beneish M-Score and Altman Z-Score — both explicitly adapted for financial institutions, since the textbook formulas assume a non-financial company's balance sheet (see [Methodology](METHODOLOGY.md) for exactly which terms were modified and why). Presenting an unmodified score as if it applied cleanly to lenders would have been analytically dishonest, so every adapted score is labeled as such everywhere it appears — in the code, the dashboard, and the memo.
- **Automated Data-Integrity Reconciliation Check**: After catching a discrepancy between a drafted memo figure and the canonical database during development, I built a permanent script ([`sql/reconcile_memo.py`](sql/reconcile_memo.py)) that parses every number cited in the investment memo and verifies it against the live database on every pipeline run. It's now part of the standard build ([`run_pipeline.py`](run_pipeline.py)).
- **Institutional Investment Memo**: A written investment memo on Upstart Holdings (`UPST`), structured like a real sell-side note — thesis, evidence, risks, valuation, and an explicit recommendation, with every claim traceable to a specific pipeline output.

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
│  • Executive Threat Matrix & Popovers   │       │  • Reconciled Trajectory vs. Live DB    │
└─────────────────────────────────────────┘       └─────────────────────────────────────────┘
```

---

## Headline Findings

1. **Pagaya (`PGY`)**: 23 flagged restatements coincide directly with a 10-K/A amendment spanning three fiscal years — and with the company landing in the Altman Z-Score distress zone the same period.
2. **Enova (`ENVA`)**: Silently shifted its receivables accounting to fair-value option treatment after 2019 — invisible unless you're checking which XBRL tag a company reports under year over year.
3. **Upstart (`UPST`)**: 2025 "recovery" is bifurcated: GAAP net income turned positive for the first time since 2021 ($+53.6M), but operating cash flow relapsed negative ($-147.7M), total debt hit an all-time high ($1.83B; D/E 2.29x), and its Altman Z-Score slipped back into the distress zone (1.71) — while the market was pricing it at 82x earnings, a ~5x premium to peer median. **Recommendation: AVOID / HIGH RISK**.
4. **Chronic Distress Runs**: Four companies (`LC`, `OPRT`, `SOFI`, `OMF`) show chronic multi-year runs in the distress zone rather than one-off cyclical dips — a materially different risk profile than a temporary downturn.

---

## 📈 Cross-Sectional Valuation Benchmark (FY2025)

| Ticker | Company Name | Market Cap ($B) | Revenue ($M) | Net Income ($M) | Shareholders' Equity ($M) | P/S | P/B | P/E | Solvency Risk Profile |
|:-------|:-------------|:---------------:|:------------:|:---------------:|:-------------------------:|:---:|:---:|:---:|:----------------------|
| **AFRM** | Affirm Holdings | $21.96B | $3,224.4M | $+52.2M | $3,069.0M | 6.81x | 7.15x | 420.7x | Distress Zone ($Z = 1.65$) |
| **ENVA** | Enova International | $3.94B | $3,151.7M | $+308.4M | $1,336.7M | 1.25x | 2.95x | 12.8x | Distress Zone ($Z = 1.77$) |
| **LC**   | LendingClub | $2.22B | $961.5M | $+135.7M | $1,500.4M | 2.31x | 1.48x | 16.4x | Distress Zone ($Z = 0.34$) |
| **OMF**  | OneMain Holdings | $8.00B | $5,455.0M | $+783.0M | $3,401.0M | 1.47x | 2.35x | 10.2x | Distress Zone ($Z = 0.84$) |
| **OPRT** | Oportun Financial | $0.24B | $956.7M | $+25.2M | $390.1M | 0.25x | 0.61x | 9.4x | Distress Zone ($Z = 0.56$) |
| **PGY**  | Pagaya Technologies | $1.70B | $1,301.4M | $+81.4M | $480.0M | 1.31x | 3.55x | 20.9x | Grey Zone ($Z = 1.87$) |
| **SEZL** | Sezzle Inc. | $2.22B | $450.3M | $+133.1M | $169.8M | 4.93x | 13.08x | 16.7x | **Safe Zone ($Z = 8.55$)** |
| **SOFI** | SoFi Technologies | $33.87B | $619.4M | $+481.3M | $10,489.5M | 54.69x | 3.23x | 70.4x | Distress Zone ($Z = 0.65$) |
| **UPST** | **Upstart Holdings** | **$4.41B** | **$1,043.9M** | **$+53.6M** | **$798.8M** | **4.22x** | **5.52x** | **82.25x** | **Distress Zone ($Z = 1.71$)** |
| **MEDIAN**| **Peer Group Median** | **$2.22B** | **$1,043.9M** | **$+133.1M** | **$1,336.7M** | **2.31x** | **3.23x** | **16.68x** | — |

---

## Tech Stack

- **Data Sourcing & ETL**: Python (`requests`, `pandas`) · SEC EDGAR XBRL API · `yfinance` (market capitalization)
- **Database & Storage**: SQLite (`data/normalized/financials.db`) · Tidy CSV exports
- **SQL Analytics Showcase**: Production SQL (window functions `LAG`/`LEAD`/`DENSE_RANK`, multi-table CTEs, self-joins) in [`sql/`](sql/)
- **Dashboards & BI**: Streamlit + Plotly (interactive app) · Tableau Public (denormalized BI layer in [`data/exports/`](data/exports/))
- **Forensic Modeling**: Adapted Beneish M-Score · Adapted Altman Z-Score · Accruals (TATA) · Growth Divergence
- **Document Generation**: Markdown $\rightarrow$ Headless Chromium/Edge (2-page institutional PDF memo)

---

## Repository Structure

```
├── ingestion/        # SEC EDGAR pull + XBRL tag normalization
├── ratios/           # Ratio engine (profitability, leverage, efficiency)
├── anomaly/          # Adapted Beneish M-Score, Altman Z-Score, accruals, growth divergence
├── dashboard/        # Streamlit interactive application
├── sql/              # Standalone analytical SQL queries + reconciliation check
├── memo/             # Investment memo (Markdown + 2-Page PDF)
├── data/
│   ├── raw/          # Cached raw SEC EDGAR company facts (JSON)
│   ├── normalized/   # Tidy SQLite DB (financials.db) + CSV exports
│   └── exports/      # Tableau Public export + institutional data dictionary
├── docs/PRD.md       # Original project specification
└── METHODOLOGY.md    # Full documentation of every adaptation and design decision
```

---

## How to Run

```bash
# Clone the repository
git clone https://github.com/Yusuffff101/automated-equity-research-desk.git
cd automated-equity-research-desk

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (single command)
python run_pipeline.py
```

Single command runs the full pipeline — ingestion, ratio calculation, anomaly detection, SQL showcase refresh, Tableau export, automated memo reconciliation check, and memo regeneration — end to end in under 6 seconds.

To launch the interactive dashboard:
```bash
streamlit run dashboard/app.py
```

---

## A Note on the Data

All financial data in this project is real, pulled live from SEC EDGAR's public API for actual SEC filers — not simulated, synthetic, or pre-cleaned. Market data is from Yahoo Finance. The only "fabricated" element is the intentional adaptation of two forensic scoring models to fit the financial-institution sector, and every adaptation is documented in [METHODOLOGY.md](METHODOLOGY.md).

---

## Future Work

Deliberately out of scope for this build, to keep it shippable:
- **Live/real-time data refresh**: Current pull is a static snapshot; re-running the pipeline updates it.
- **Full DCF modeling**: The memo uses a lightweight relative-valuation comparison instead (standard sell-side practice for lenders).
- **Multi-sector coverage**: Tailored specifically to fintech and specialty consumer lending to maintain accounting precision.
- **Predictive/ML modeling**: Kept as a separate, distinct project.

---

*Educational/portfolio research project based on public SEC filings. Not investment advice.*
