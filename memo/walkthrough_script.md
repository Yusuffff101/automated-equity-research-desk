# 🎙️ Spoken Walkthrough Script: Automated Equity Research Desk

> **Target Duration:** ~2:00 spoken video recording  
> **Interview Mode:** Expandable to 5:00 unscripted deep-dive per PRD §12  
> **Speaker Pace:** Confident, conversational, analytical (~150 words per minute)

---

## ⏱️ Two-Minute Spoken Script

### Part 1: The Hook & The Problem [0:00 – 0:25]
*(Looking at camera or project title slide)*

> "Most fintech dashboard projects on GitHub are toys: they download a pre-cleaned CSV from Kaggle, calculate a generic P/E ratio, and call it financial analysis. 
> 
> But in the real world, fintech lenders don't have Cost of Goods Sold, they don't report classified balance sheets with Current Assets, and their 10-Ks are messy, restated, and governed by complex accounting rules like CECL and Fair Value Option. 
> 
> I built the **Automated Equity Research Desk** to bridge that gap—an autonomous end-to-end pipeline that pulls real SEC EDGAR data, adapts institutional forensic models for lenders, and produces an actionable investment thesis."

---

### Part 2: The Pipeline Architecture [0:25 – 0:50]
*(Screen recording shows `run_pipeline.py` terminal execution or Architecture Diagram)*

> "The pipeline runs end-to-end with a single command: `python run_pipeline.py`. 
> 
> First, it harvests 100% real XBRL company facts directly from the SEC EDGAR API across 9 public consumer lenders like Affirm, SoFi, and Upstart from 2021 to 2026. 
> 
> Because financial institutions use disparate tagging, our normalizer maps custom fallback tags, detects 10-K/A restatements, and stores over 800 normalized facts in a local SQLite database. 
> 
> Next, our ratio engine computes 540 financial ratios across profitability, credit leverage, and efficiency—strictly enforcing domain guardrails like explicitly labeling gross margin as 'Not Applicable' for balance-sheet lenders."

---

### Part 3: Forensic Anomaly Detection in Action [0:50 – 1:15]
*(Screen recording switches to Dashboard: Executive Threat Matrix & Forensic Container)*

> "Next, the adapted anomaly module runs. Standard models like Beneish M-Score and Altman Z-Score break on financial institutions because there's no gross margin or working capital. 
> 
> We adapted them: dropping GMI from Beneish, and substituting Cash for Working Capital in Altman Z. 
> 
> And it caught genuine red flags: for example, **Pagaya Technologies (`PGY`)** had a formal SEC 10-K/A restatement coinciding with our adapted Altman Z-Score flagging severe insolvency risk at 1.39 in the Distress Zone. 
> 
> It also caught **Upstart's 2022 inventory blowup**, where receivables spiked +300% when loan buyers vanished, triggering an elevated Beneish score of +1.28 and our growth divergence warning."

---

### Part 4: The Upstart Investment Thesis [1:15 – 1:40]
*(Screen recording displays the 2-page PDF memo: `memo/UPST_investment_memo.pdf`)*

> "That forensic power drives our investment memo on **Upstart Holdings (`NASDAQ: UPST`)**, where we initiated with an **AVOID / HIGH RISK** call. 
> 
> The consensus narrative was that Upstart suffered a rate shock in 2022 and has cleanly recovered. But when our pipeline audited the full 2021 to 2025 trajectory, we found the recovery is bifurcated. 
> 
> Yes, revenue grew +64% to over $1 billion and reported GAAP net income hit positive $54 million. But underneath, operating cash flow collapsed back to **negative $148 million**, total debt reached an all-time high of **$1.39 billion**, and its **Adapted Altman Z-Score relapsed right back into the Distress Zone at 1.71**. 
> 
> At **82x earnings**—nearly five times the peer median—the market is pricing Upstart as an asset-light software pure play, ignoring its leveraged balance-sheet reality."

---

### Part 5: The Live Dashboard Demo & Wrap-Up [1:40 – 2:00]
*(Screen recording tours Streamlit interface: interactive hover states, outlier clipping, and conclusion)*

> "Finally, the findings come alive in our interactive Streamlit terminal. Analysts can compare multi-year peer trajectories, inspect outlier-clipped charts so extreme values don't distort trends, and review the Executive Threat Matrix. 
> 
> With a single click, it exports our publication-ready 2-page PDF note. 
> 
> The entire project is open-source, fully reproducible, and deployed live. Check out the link in the repository to explore the terminal yourself. Thank you!"

---

## 🎓 5-Minute Unscripted Interview Defense Guide

If an interviewer asks you to walk through the project in depth, use these five structural anchors to control the dialogue:

### 1. Data Engineering & XBRL Nuances (1:00)
- **Talk about SEC EDGAR rate limits**: Implemented polite request throttling (10 requests/sec max) with declared institutional User-Agent per SEC compliance.
- **Handling FYE Mismatches**: Affirm (`AFRM`) and Sezzle (`SEZL`) have June fiscal year-ends, whereas Upstart and SoFi use December 31. Explain how you aligned them to calendar years using nearest annual filings with explicit methodology notes.
- **Tag Discrepancies**: Lenders don't use standard `LongTermDebt`. You had to map `DebtLongtermAndShorttermCombinedAmount` for Upstart and warehouse credit lines for Oportun and Enova.

### 2. Forensic Modeling Adaptations (1:00)
- **Beneish M-Score ex-GMI**: Explain why Gross Margin Index (GMI) had to be mathematically removed, and how you audited the remaining 7 indices (DSRI, AQI, SGI, DEPI, SGAI, TATA, LVGI).
- **Altman Z-Score Cash/TA Substitution**: Explain why Working Capital ($WC = CA - CL$) fails for unclassified lender balance sheets. Substituting $Cash / Total Assets$ preserves the intended liquidity measurement without introducing synthetic zeroes.
- **Accruals Ratio (TATA)**: Highlight why $(Net Income - CFO) / Total Assets$ is the ultimate truth detector for Upstart in 2025.

### 3. Concrete Red Flags Discovered (1:00)
- **Pagaya (`PGY`)**: 10-K/A restatement + Altman Z = 1.39 (Distress Zone).
- **Enova (`ENVA`)**: Fair Value Option (FVO) portfolio shifts obscuring traditional credit allowances.
- **Upstart (`UPST`)**: 2022 loan inventory spike ($+300\%$ receivables) leading to the 2025 cash burn relapse.

### 4. Valuation Rigor & Macro Synthesis (1:00)
- **Why No DCF?**: Defend the decision not to build a DCF model. Banks and lenders borrow money as raw inventory; Free Cash Flow to Firm is distorted by debt changes. Relative multiples ($P/E, P/S, P/B$) anchored against credit leverage are the industry standard.
- **The Upstart Mispricing**: Contrast UPST at 82.3x P/E with profitable, high-performing comps like Sezzle at 16.7x P/E with Altman Z = 8.55 (Safe Zone).

### 5. UI/UX Design System (1:00)
- **Outlier Bounding**: Show how Sezzle's $-430\%$ ROE in 2022 would have squashed everyone else's lines to flat strings if you hadn't implemented programmatic axis clamping.
- **Explicit N/A States**: Distinguish between pre-IPO missing data (gapped line with hover explanation) vs. zero value drops.
