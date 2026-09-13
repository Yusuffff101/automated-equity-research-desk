"""
dashboard/components/methodology_guide.py — Interactive Methodology & User Guide.

Provides self-explanatory institutional context for recruiters and analysts
without requiring them to read external README or documentation files.
"""

import streamlit as st


def render_methodology_guide() -> None:
    """Render interactive methodology reference."""
    st.markdown("### ℹ️ Executive Methodology & Adaptation Guide")
    st.markdown(
        "A self-contained analytical reference explaining why classical corporate distress and forensic models "
        "were adapted for technology-driven consumer lenders and specialty finance institutions."
    )

    with st.expander("❓ Why Standard Financial Models Fail for Consumer Lenders", expanded=True):
        st.markdown(
            """
            Classical forensic and solvency models (Altman Z-Score 1968, Beneish M-Score 1999) were empirically calibrated on **manufacturing and non-financial corporations**:
            
            1. **No Cost of Goods Sold (COGS)**:
               - Beneish's *Gross Margin Index (GMI)* requires $(\\text{Revenue} - \\text{COGS}) / \\text{Revenue}$.
               - Consumer lenders generate revenue from net interest margins, gain-on-sale, and origination fees — they have no inventory or raw material COGS.
               - *Adaptation*: We explicitly drop $+0.528 \\cdot \\text{GMI}$ and adjust the intercept to $-4.493$.
            
            2. **Unclassified Balance Sheets (No Current/Non-Current Asset Split)**:
               - Altman's $X_1 = \\text{Working Capital} / \\text{Total Assets}$ requires $(\\text{Current Assets} - \\text{Current Liabilities})$.
               - Financial institutions do not classify customer loans or warehouse credit facilities into current vs non-current buckets.
               - *Adaptation*: We substitute **Cash & Cash Equivalents / Total Assets** $(\\text{Cash} / \\text{TA})$, representing the truest immediate liquidity buffer.
            
            3. **Securitization & Off-Balance-Sheet Receivables (PGY & ENVA)**:
               - Pagaya transfers loans into ABS securitization trusts immediately; Enova accounts for loans under ASC 825 Fair Value Option.
               - Standard receivables growth divergence is structurally inapplicable and is assigned **Explicit N/A**.
            """
        )

    with st.expander("📐 Mathematical Formulas & Threshold Interpretations", expanded=True):
        st.markdown(
            """
            | Model / Metric | Adaptation Formula | Risk Thresholds & Interpretation |
            |:---------------|:-------------------|:---------------------------------|
            | **Adapted Altman Z-Score** | $Z = 1.2(\\frac{\\text{Cash}}{\\text{TA}}) + 1.4(\\frac{\\text{RE}}{\\text{TA}}) + 3.3(\\frac{\\text{EBIT}}{\\text{TA}}) + 0.6(\\frac{\\text{MVE}}{\\text{TL}}) + 0.999(\\frac{\\text{Sales}}{\\text{TA}})$ | • **Distress Zone:** $Z < 1.81$<br>• **Grey Zone:** $1.81 \\le Z \\le 2.99$<br>• **Safe Zone:** $Z > 2.99$ |
            | **Adapted Beneish M-Score** | $M = -4.493 + 0.920\\text{DSRI} + 0.892\\text{SGI} + 4.037\\text{TATA} + 0.0327\\text{LVGI}$ | • **Cutoff:** $-1.78$<br>• **Directional Signal:** Scores above $-1.78$ indicate elevated risk of aggressive revenue/accrual booking relative to peers. |
            | **Accruals Ratio** | $\\text{Accruals} = \\frac{\\text{Net Income} - \\text{Operating Cash Flow}}{\\text{Total Assets}}$ | • **High Accruals Risk:** $> +10\\%$ (Earnings unbacked by cash)<br>• **Strong Conversion:** $< -10\\%$ (Operating cash exceeds GAAP NI) |
            | **Growth Divergence** | $\\Delta = \\text{YoY Receivables Growth} - \\text{YoY Revenue Growth}$ | • **Divergence Risk:** $> +15\\%$ spread signals aggressive credit origination or delayed non-accrual marks.<br>• *Exempt for PGY & ENVA*. |
            """
        )

    with st.expander("🏷️ Data Quality Flag Taxonomy", expanded=False):
        st.markdown(
            """
            Every data point in the desk carries a verifiable data-quality provenance tag:
            
            - **`OK`**: Primary XBRL tag located; authoritative single filing.
            - **`COMPARATIVE`**: Prior-period figure appearing in later filings with identical value (routine SEC disclosure).
            - **`FALLBACK`**: Primary tag missing; mapped to semantically verified alternative fallback tag.
            - **`RESTATED`**: Value changed in subsequent 10-K or amended via a **10-K/A** filing (e.g. Pagaya FY2024).
            - **`PRE_IPO_UNAVAILABLE`**: Company was not publicly traded as of year-end (e.g. Sezzle 2021–2022). Zero is never substituted.
            - **`NOT_APPLICABLE`**: Metric is structurally inapplicable to the business model (e.g. receivables turnover for PGY/ENVA).
            - **`MISSING_DATA`**: Tag unpopulated in SEC filing or pending future 10-K filing.
            """
        )

    with st.expander("🏢 Coverage Universe (9 Comparable Public Constituents)", expanded=False):
        st.markdown(
            """
            | Ticker | Company | Model Type | Core Accounting Characteristic |
            |:-------|:--------|:-----------|:-------------------------------|
            | **AFRM** | Affirm Holdings | BNPL Platform | Gain-on-sale origination; June 30 fiscal year-end |
            | **SEZL** | Sezzle Inc. | BNPL Platform | High merchant fee conversion; 2023–2025 profitability turnaround |
            | **UPST** | Upstart Holdings | AI Lending Marketplace | 2022 Fed rate hike loan-inventory shock & partner warehouse contraction |
            | **SOFI** | SoFi Technologies | Digital Bank & FinTech | Post-bank-charter deposit funding & CECL provision ramp |
            | **LC**   | Happen Inc. (fka LendingClub) | Marketplace Bank | Transitioned from P2P marketplace to FDIC-insured chartered bank |
            | **PGY**  | Pagaya Technologies | AI Credit Network | Institutional ABS partner network; FY24 10-K/A restatement |
            | **OPRT** | Oportun Financial | Subprime Consumer Credit | Near-prime/subprime personal loans; elevated credit charge-offs |
            | **OMF**  | OneMain Holdings | Legacy Branch/Online Lender | Mature benchmark anchor; secured auto & personal installment loans |
            | **ENVA** | Enova International | Multi-Brand Online Lender | High-APR specialty credit; loans carried under ASC 825 Fair Value Option |
            """
        )
