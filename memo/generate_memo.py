"""
memo/generate_memo.py — Generate 2-Page Institutional Investment Memo for UPST.

Outputs:
  - memo/UPST_investment_memo.md (Clean GitHub Markdown)
  - memo/UPST_investment_memo.html (Styled 2-page print HTML)
  - memo/UPST_investment_memo.pdf (Rendered 2-page PDF via Chromium/Edge print engine)
"""

import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import markdown
from config import SQLITE_PATH

MEMO_DIR = PROJECT_ROOT / "memo"
MD_PATH = MEMO_DIR / "UPST_investment_memo.md"
HTML_PATH = MEMO_DIR / "UPST_investment_memo.html"
PDF_PATH = MEMO_DIR / "UPST_investment_memo.pdf"

MEMO_MARKDOWN_CONTENT = """# EQUITY RESEARCH INSTITUTIONAL NOTE

**TICKER:** NASDAQ: UPST | **PRICE:** $44.96 | **MARKET CAP:** $4.41B | **RATING: AVOID / HIGH RISK**  
**COVERAGE:** Fintech & AI-Driven Lending Desk | **DATE:** September 2026 | **ANALYST:** Automated Equity Research Desk

---

## 1. Executive Investment Thesis

**We initiate coverage on Upstart Holdings, Inc. (NASDAQ: UPST) with an AVOID / HIGH RISK rating.** While Upstart's topline re-accelerated to $1,043.9M (+64.0% YoY) and reported GAAP net income inflected to $+53.6M (ROE +6.71%) in FY2025, the underlying balance sheet has relapsed into financial fragility: operating cash flow flipped negative to **$-147.7M** (creating $+201.3M in non-cash accruals), total debt reached an all-time high of **$1.83B** (debt-to-equity of 2.29x), and the **Adapted Altman Z-Score slipped back into the Distress Zone at 1.71 (< 1.81)**. Trading at an extreme valuation of **82.3x P/E** and **4.22x P/S** (an 83% premium to the peer median), the equity market is pricing UPST as a capital-light software platform rather than a balance-sheet-constrained lender vulnerable to liquidity and credit headwinds.

---

## 2. Step 0 Empirical Audit: The "Turnaround" Is Bifurcated & Incomplete

Our automated pipeline evaluated Upstart's complete longitudinal trajectory (FY2021–FY2025) across operational ratios, capital structure, and forensic anomaly models. The data reveals that the assumed "clean recovery" from the 2022 Fed rate shock is heavily bifurcated between income statement metrics and balance sheet reality:

### Upstart Holdings (UPST) — Historical Trajectory & Forensic Model Audit
| Metric / Indicator | FY2021 (Peak Bubble) | FY2022 (Rate Shock) | FY2023 (Trough) | FY2024 (Offloading) | FY2025 (Re-acceleration) | Forensic Signal & Sector Interpretation |
|:-------------------|:--------------------:|:-------------------:|:---------------:|:-------------------:|:------------------------:|:----------------------------------------|
| **Revenue ($M)** | $848.6M | $842.4M (-0.7%) | $513.6M (-39.0%) | $636.5M (+23.9%) | **$1,043.9M (+64.0%)** | Topline recovered beyond 2021 levels. |
| **GAAP Net Income ($M)** | $+135.4M | $-108.7M | $-240.1M | $-128.6M | **$+53.6M** | First profitable year since 2021. |
| **Operating Cash Flow ($M)** | $+168.4M | **$-657.9M** | $-111.7M | $+186.3M | **$-147.7M** | **RELAPSED NEGATIVE**: GAAP profit unbacked by cash. |
| **Accruals Ratio (TATA)** | -0.018 | **+0.284** | -0.064 | -0.133 | **+0.068** | $+201.3M non-cash accruals (+6.8% of assets). |
| **Total Debt ($M)** | $695.4M | $986.4M | $1,040.4M | $1,402.2M | **$1,829.1M** | All-time high leverage ($1.83B total debt; D/E 2.29x). |
| **Total Liabilities ($M)** | $1,013.4M | $1,263.6M | $1,381.8M | $1,733.7M | **$2,176.0M** | Liabilities expanded +25.5% YoY in FY25. |
| **Shareholders' Equity ($M)**| $807.1M | $672.4M | $635.3M | $633.2M | **$798.8M** | Dilution & stock comp rebuilt equity buffer. |
| **Interest Coverage** | +43.03x | -10.50x | -7.35x | N/A | **N/A** | Vulnerable buffer; interest expense omitted on 10-K face in 2024-25. |
| **Return on Equity (ROE)** | +16.78% | -16.16% | -37.80% | -20.31% | **+6.71%** | Positive accounting return on equity. |
| **Return on Assets (ROA)** | +7.44% | -5.61% | -11.90% | -5.43% | **+1.80%** | Thin balance-sheet return on assets. |
| **Growth Divergence** | N/A ($t_0$) | **+300.9%** | +53.5% | -54.2% | -41.9% | Normalized as revenue outpaced loan buildup. |
| **Beneish M-Score (Adapted)**| N/A ($t_0$) | **+1.28 (ELEVATED)**| -2.44 | -3.37 | -2.04 (Low Risk) | 2022 flag captured $+300%$ receivables surge. |
| **Altman Z-Score (Adapted)** | **8.51 (Safe)** | **0.72 (Distress)** | **1.39 (Distress)** | **2.24 (Grey)** | **1.71 (DISTRESS)** | **RELAPSED INTO DISTRESS ZONE (< 1.81)**. |

1. **The 2022 Rate Shock Deconstructed**: When the Federal Reserve hiked interest rates in 2022, Upstart's loan buyers halted commitments. Net income collapsed to $-108.7M and operating cash flow burned **$-657.9M**. Loan receivables surged +300.2% (from $252M to $1,010M) as loans became trapped on Upstart's balance sheet, triggering our module's **Growth Divergence warning (+300.9%)**, an **Adapted Beneish M-Score of +1.28 (Elevated Risk)**, and plunging the Adapted Altman Z-Score to **0.72 (Distress Zone)**.
2. **The 2024 False Dawn**: In FY2024, Upstart offloaded trapped inventory, driving receivables down -30.3% ($1,156M to $806M), producing $+186.3M in CFO and an Accruals Ratio of -0.133. This pushed the Adapted Altman Z-Score into the **Grey Zone at 2.24**.
3. **The 2025 Relapse**: While FY2025 revenue surged +64.0% to $1,043.9M, Upstart again expanded balance sheet commitments: loan assets grew +22.1% to $985M, total debt rose to a record **$1,829.1M**, and CFO flipped back to **$-147.7M**. As a consequence, the **Adapted Altman Z-Score relapsed to 1.71 (Distress Zone)**.

<div class="page-break"></div>

## 3. Solvency & Balance Sheet Fragility Analysis

The Adapted Altman Z-Score demonstrates why equity investors are taking disproportionate downside risk:
- **Cash Liquidity Squeeze ($X_1$)**: Cash & equivalents dropped from $788M (FY24) to $652M (FY25), reducing the Cash/TA liquidity buffer from 0.33 to 0.22.
- **Accumulated Deficit Drag ($X_2$)**: Cumulative operating losses left Retained Earnings at **$-358M** (RE/TA = -0.12), depressing the baseline solvency score.
- **Leverage Acceleration ($X_4$)**: Total liabilities expanded by **$442.3M (+25.5% YoY)** to $2.18B. Market capitalization fell from $5.93B to $4.41B, driving the equity cushion (MVE/TL) down from 3.42x to 2.03x.
- **Tenuous Coverage**: Operating buffer remains razor-thin: FY2025 EBIT is only **$42.6M** (4.1% operating margin), while interest expense is omitted from the 10-K face as borrowings shifted to warehouse credit facilities. With **$1.83B in total debt** and operating cash burn of **$-147.7M**, Upstart lacks the operating cushion to absorb higher credit charge-offs or funding cost spikes.

---

## 4. Relative Valuation: Extreme Multiple Premium vs. Peer Group

We benchmarked Upstart against all 8 publicly traded peers in our fintech and specialty lending coverage universe:

### FY2025 Relative Valuation Multiples & Capital Structure Comparison
| Ticker | Company Name | Market Cap ($B) | Revenue ($M) | Net Income ($M) | Shareholders' Equity ($M) | P/S Multiple | P/B Multiple | P/E Multiple | Solvency Profile (Z-Score) |
|:-------|:-------------|:---------------:|:------------:|:---------------:|:-------------------------:|:------------:|:------------:|:------------:|:--------------------------:|
| **AFRM** | Affirm Holdings | $21.96B | $3,224.4M | $+52.2M | $3,069.0M | 6.81x | 7.15x | 420.7x | Distress Zone (Z = 1.65) |
| **ENVA** | Enova International | $3.94B | $3,151.7M | $+308.4M | $1,336.7M | 1.25x | 2.95x | 12.8x | Distress Zone (Z = 1.77) |
| **LC**   | Happen Inc. (LendingClub) | $2.22B | $961.5M | $+135.7M | $1,500.4M | 2.31x | 1.48x | 16.4x | Distress Zone (Z = 0.34) |
| **OMF**  | OneMain Holdings | $8.00B | $5,455.0M | $+783.0M | $3,401.0M | 1.47x | 2.35x | 10.2x | Distress Zone (Z = 0.84) |
| **OPRT** | Oportun Financial | $0.24B | $956.7M | $+25.2M | $390.1M | 0.25x | 0.61x | 9.4x | Distress Zone (Z = 0.56) |
| **PGY**  | Pagaya Technologies | $1.70B | $1,301.4M | $+81.4M | $480.0M | 1.31x | 3.55x | 20.9x | Grey Zone (Z = 1.87) |
| **SEZL** | Sezzle Inc. | $2.22B | $450.3M | $+133.1M | $169.8M | 4.93x | 13.08x | 16.7x | **Safe Zone (Z = 8.55)** |
| **SOFI** | SoFi Technologies | $33.87B | $619.4M | $+481.3M | $10,489.5M | 54.69x | 3.23x | 70.4x | Distress Zone (Z = 0.65) |
| **UPST** | **Upstart Holdings** | **$4.41B** | **$1,043.9M** | **$+53.6M** | **$798.8M** | **4.22x** | **5.52x** | **82.25x** | **Distress Zone (Z = 1.71)** |
| **MEDIAN**| **Peer Group Median** | **$2.22B** | **$1,043.9M** | **$+133.1M** | **$1,336.7M** | **2.31x** | **3.23x** | **16.68x** | — |

- **P/E Ratio of 82.25x**: UPST trades at **4.93x the median profitable peer multiple (16.68x)**. Profitable, established consumer lenders like Enova (12.8x), LendingClub (16.4x), and OneMain (10.2x) trade at single-digit to mid-teen earnings multiples.
- **P/S Ratio of 4.22x**: UPST trades at an **83% premium** over the peer median of 2.31x.
- **P/B Ratio of 5.52x**: UPST trades at a **71% premium** over the peer median of 3.23x.

---

## 5. Key Catalysts & Investment Risks

### Downside Risks (Supporting AVOID Call):
1. **Balance-Sheet Capacity Ceiling**: With total debt at $1.83B (D/E of 2.29x) and operating cash flow negative ($-147.7M), Upstart cannot fund origination growth internally. Any hesitation among institutional ABS partners will force originations back onto the balance sheet, triggering a repeat of the 2022 inventory blowup.
2. **Multiple Compression Threat**: If the market re-rates UPST from an "AI platform" (82x P/E) toward high-growth profitable fintech peers like Sezzle (16.7x P/E) or Pagaya (20.9x P/E), the stock faces **60% to 75% downside re-rating risk**.
3. **Credit Cycle Reversal**: Razor-thin operating profit ($42.6M EBIT) and recurring cash burn ($-147.7M CFO) leave zero cushion for rising net charge-offs or credit provision adjustments under CECL accounting.


### Upside Risks (What Would Invalidate Our Thesis):
1. **Committed Capital Acceleration**: Long-term, non-call institutional co-investment agreements exceeding 70% of total originations that eliminate balance sheet credit risk.
2. **Sustained Free Cash Flow Inflection**: Operating cash flow exceeding $+150M in FY2026, lowering debt and lifting Adapted Altman Z-Score above 2.50.

---

## 6. Conclusion & Recommendation

**RECOMMENDATION: AVOID / HIGH RISK | VALUATION ASSESSMENT: OVERVALUED**  
Upstart has proven the elasticity of its AI origination algorithms, but it has not resolved its structural reliance on warehouse credit and institutional partner liquidity. At **82.3x P/E**, investors are paying a premium software multiple for a business sitting in the **Altman Z Distress Zone (Z = 1.71)** with recurring cash burn ($-147.7M CFO). We advise institutional investors to avoid UPST or rotate into higher-quality, cash-generative peers (e.g. Sezzle at 16.7x P/E with Safe Zone Z = 8.55).

---

<div class="disclaimer">Educational/portfolio research exercise based on public SEC filings; not investment advice.</div>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Upstart Holdings (UPST) — Institutional Equity Research Memo</title>
    <style>
        @page {
            size: letter;
            margin: 0.45in 0.5in 0.45in 0.5in;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 8.5pt;
            line-height: 1.35;
            color: #1e293b;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
        }
        .disclaimer {
            font-size: 6.8pt;
            color: #64748b;
            font-style: italic;
            text-align: center;
            margin-top: 4px;
            padding-top: 2px;
        }
        h1 {
            font-size: 14pt;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 4px 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #2563eb;
            padding-bottom: 3px;
        }
        h2 {
            font-size: 10pt;
            font-weight: 700;
            color: #1e3a8a;
            margin: 8px 0 4px 0;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 2px;
        }
        h3 {
            font-size: 8.5pt;
            font-weight: 700;
            color: #334155;
            margin: 6px 0 2px 0;
        }
        p {
            margin: 0 0 5px 0;
            text-align: justify;
        }
        strong {
            color: #0f172a;
            font-weight: 700;
        }
        hr {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 6px 0;
        }
        .page-break {
            page-break-after: always;
            break-after: page;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 7.2pt;
            margin: 5px 0 7px 0;
        }
        th {
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: 700;
            text-align: center;
            padding: 3px 4px;
            border: 1px solid #cbd5e1;
            white-space: nowrap;
        }
        td {
            padding: 2.5px 4px;
            border: 1px solid #e2e8f0;
            text-align: center;
        }
        td:first-child {
            text-align: left;
            font-weight: 600;
        }
        tr:nth-child(even) {
            background-color: #f8fafc;
        }
        ul, ol {
            margin: 0 0 5px 0;
            padding-left: 16px;
        }
        li {
            margin-bottom: 2px;
        }
        .header-box {
            background-color: #f8fafc;
            border: 1px solid #cbd5e1;
            border-left: 4px solid #dc2626;
            padding: 5px 8px;
            margin-bottom: 8px;
            font-size: 8pt;
        }
    </style>
</head>
<body>
__CONTENT__
</body>
</html>
"""


def generate_memo() -> None:
    """Generate Markdown, HTML, and PDF versions of the memo."""
    MEMO_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Write Markdown
    MD_PATH.write_text(MEMO_MARKDOWN_CONTENT, encoding="utf-8")
    print(f"Wrote Markdown memo: {MD_PATH}")

    # 2. Convert to HTML
    html_body = markdown.markdown(
        MEMO_MARKDOWN_CONTENT,
        extensions=["extra", "tables"],
    )
    full_html = HTML_TEMPLATE.replace("__CONTENT__", html_body)
    HTML_PATH.write_text(full_html, encoding="utf-8")
    print(f"Wrote HTML memo: {HTML_PATH}")

    # 3. Render PDF
    # Attempt Edge / Chrome headless printing
    edge_bin = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    chrome_bin = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    browser_bin = None

    if os.path.exists(edge_bin):
        browser_bin = edge_bin
    elif os.path.exists(chrome_bin):
        browser_bin = chrome_bin
    else:
        browser_bin = shutil.which("msedge") or shutil.which("chrome")

    if browser_bin:
        cmd = [
            browser_bin,
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={PDF_PATH.resolve()}",
            str(HTML_PATH.resolve()),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and PDF_PATH.exists():
            print(f"Rendered PDF via Chromium headless: {PDF_PATH} ({PDF_PATH.stat().st_size} bytes)")
            return
        else:
            print(f"Browser PDF failed: {res.stderr}")

    # Fallback to WeasyPrint if available
    try:
        import weasyprint
        weasyprint.HTML(filename=str(HTML_PATH)).write_pdf(str(PDF_PATH))
        print(f"Rendered PDF via WeasyPrint: {PDF_PATH}")
    except Exception as e:
        print(f"WeasyPrint render error: {e}")


if __name__ == "__main__":
    generate_memo()
